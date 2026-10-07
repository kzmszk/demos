// Falling snow in winter: soft flakes in a box that travels with the camera (positions wrap), drifting as they fall.
// One instanced draw; the flakes are lit by the evening sky and fade with distance.
import * as THREE from 'three/webgpu';
import { attribute, uniform, vec2, vec3, vec4, float, fract, sin, cos, mix, smoothstep, length, uv, positionLocal, cameraPosition, cameraViewMatrix,
  normalize, cross, max, min, positionWorld } from 'three/tsl';
import { G } from './kyomat.js';

export class Snow {
  constructor(scene, n = 9000, R = 28) {
    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-0.5, -0.5, 0, 0.5, -0.5, 0, 0.5, 0.5, 0, -0.5, 0.5, 0]), 3));
    g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]), 2));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    const a = new Float32Array(n * 4);
    for (let i = 0; i < n; i++) { a[i * 4] = Math.random(); a[i * 4 + 1] = Math.random(); a[i * 4 + 2] = Math.random(); a[i * 4 + 3] = Math.random(); }
    g.setAttribute('seed', new THREE.InstancedBufferAttribute(a, 4));
    g.instanceCount = n;
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e7);
    this.amount = uniform(0.0);
    const s = attribute('seed', 'vec4'), t = G.time;
    const box = float(R * 2);
    // a position inside a box around the camera: fall at ~0.9 m/s with a sway, wrapped
    const fall = t.mul(float(0.7).add(s.w.mul(0.5)));
    const local = vec3(s.x.mul(box).add(sin(t.mul(0.6).add(s.w.mul(20.0))).mul(0.6)), s.y.mul(box).add(cos(t.mul(0.5).add(s.z.mul(17.0))).mul(0.5)), s.z.mul(box).sub(fall));
    const rel = local.sub(cameraPosition).add(box.mul(0.5));
    const wrapped = vec3(fract(rel.x.div(box)), fract(rel.y.div(box)), fract(rel.z.div(box))).mul(box).sub(box.mul(0.5)).add(cameraPosition);
    // camera-facing quad, ~1.2 cm flakes
    const vm = cameraViewMatrix;          // rows of the view matrix = the camera's right / up in the world
    const right = vec3(vm.element(0).x, vm.element(1).x, vm.element(2).x);
    const up = vec3(vm.element(0).y, vm.element(1).y, vm.element(2).y);
    const size = float(0.012).add(s.w.mul(0.012));
    const mat = new THREE.MeshBasicNodeMaterial();
    mat.positionNode = wrapped.add(right.mul(positionLocal.x.mul(size))).add(up.mul(positionLocal.y.mul(size)));
    const d = length(uv().sub(0.5)).mul(2.0);
    const dist = length(wrapped.sub(cameraPosition));
    const fade = smoothstep(float(R), float(R * 0.5), dist).mul(smoothstep(0.2, 1.2, dist));
    mat.colorNode = vec3(0.75, 0.78, 0.85).mul(G.sunCol.mul(0.08).add(vec3(0.55)));
    mat.opacityNode = smoothstep(1.0, 0.2, d).mul(fade).mul(this.amount).mul(0.85);
    mat.transparent = true; mat.depthWrite = false;
    this.mesh = new THREE.Mesh(g, mat); this.mesh.frustumCulled = false; this.mesh.renderOrder = 10;
    scene.add(this.mesh);
  }
  update(on) { this.amount.value += ((on ? 1 : 0) - this.amount.value) * 0.03; this.mesh.visible = this.amount.value > 0.01; }
}
