// Canal and lagoon water at z = 0: planar reflection of the city, wind ripples, Fresnel, sun glitter.
import * as THREE from 'three/webgpu';
import { reflector, texture, uniform, vec2, vec3, vec4, float, normalize, mix, dot, pow, clamp, positionWorld, positionViewDirection, normalView, uv, Fn, cameraPosition, transformNormalToView, max } from 'three/tsl';
import { G } from './citymat.js';

class WaterMaterial extends THREE.MeshStandardNodeMaterial {
  setupEnvironment() { return null; }
}

export function makeWater(scene, nrmTex, opts = {}) {
  const refl = reflector({ resolutionScale: opts.reflScale ?? 0.5, generateMipmaps: false, bounces: false });
  scene.add(refl.target);
  // mark the mirrored cameras so shadow maps are not re-rendered for them (same light frusta as the main view)
  const base = refl.reflector, gvc = base.getVirtualCamera.bind(base);
  // the reflection sees layers 0 and 2 (coarse stand-ins), not 1 (near facades, props, full-detail heroes)
  base.getVirtualCamera = (cam) => { const vc = gvc(cam); vc.userData.reflection = true; vc.layers.mask = 1 | 4; return vc; };
  if (!THREE.ShadowNode.prototype._venPatched) {
    const ub = THREE.ShadowNode.prototype.updateBefore;
    THREE.ShadowNode.prototype.updateBefore = function (frame) { if (frame.camera && frame.camera.userData.reflection) return; return ub.call(this, frame); };
    THREE.ShadowNode.prototype._venPatched = true;
  }
  nrmTex.wrapS = nrmTex.wrapT = THREE.RepeatWrapping; nrmTex.colorSpace = THREE.NoColorSpace;
  const t = G.time;
  const wp = positionWorld.xy;
  const n1 = texture(nrmTex, wp.mul(1 / 9.0).add(vec2(t.mul(0.013), t.mul(0.007)))).xyz.mul(2).sub(1);
  const n2 = texture(nrmTex, wp.mul(1 / 3.7).add(vec2(t.mul(-0.011), t.mul(0.017)))).xyz.mul(2).sub(1);
  const n3 = texture(nrmTex, wp.mul(1 / 1.3).add(vec2(t.mul(0.021), t.mul(-0.015)))).xyz.mul(2).sub(1);
  const nT = normalize(vec3(n1.xy.mul(0.55).add(n2.xy.mul(0.45)).add(n3.xy.mul(0.25)), 1.0));
  const nW = normalize(vec3(nT.x.mul(0.5), nT.y.mul(0.5), nT.z));
  // distort reflection lookup by the ripples
  refl.uvNode = refl.uvNode.add(nW.xy.mul(0.035));
  const V = normalize(cameraPosition.sub(positionWorld));
  const cosT = clamp(dot(nW, V), 0.0, 1.0);
  const fres = float(0.02).add(float(0.98).mul(pow(float(1).sub(cosT), 5.0)));
  // murky lagoon water: scattered body colour lit by the sky (+ sun via the lighting model)
  const body = mix(vec3(0.010, 0.030, 0.024), vec3(0.003, 0.006, 0.008), G.night);
  const scatter = body.mul(mix(float(0.55), float(0.02), G.night)).mul(float(1).sub(fres));
  const mat = new WaterMaterial();
  mat.colorNode = body;
  mat.roughnessNode = float(0.06);
  mat.metalnessNode = float(0.0);
  mat.normalNode = transformNormalToView(nW);
  mat.emissiveNode = refl.rgb.mul(fres).mul(0.98).add(scatter);
  const geo = new THREE.PlaneGeometry(9000, 6000, 1, 1);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(-400, 0, 0); mesh.receiveShadow = true; mesh.castShadow = false;
  scene.add(mesh);
  return { mesh, refl };
}
