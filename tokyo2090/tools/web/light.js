import * as THREE from 'three';

// The sun and its shadow. One directional light with a 4096 shadow map that follows the camera (a 2.2 km box
// ahead of it); the custom materials sample the map themselves through `shadowMap` / `shadowMatrix` uniforms,
// and the city meshes carry a depth material that decodes their packed vertices.

export const shadowGLSL = /* glsl */`
  uniform sampler2D shadowMap; uniform mat4 shadowMatrix; uniform vec2 shadowSize;
  float shadowAt(vec3 w, vec3 N, vec3 L){
    vec4 sc = shadowMatrix * vec4(w + N * 0.6, 1.0); sc.xyz /= sc.w;
    if(sc.x <= 0.001 || sc.x >= 0.999 || sc.y <= 0.001 || sc.y >= 0.999 || sc.z >= 1.0) return 1.0;
    float bias = 0.0012 + 0.002 * (1.0 - max(dot(N, L), 0.0));
    float s = 0.0; vec2 t = 1.0 / shadowSize;
    for(int i = -1; i <= 1; i++) for(int j = -1; j <= 1; j++){
      float d = unpackRGBAToDepth(texture2D(shadowMap, sc.xy + vec2(float(i), float(j)) * t));
      s += sc.z - bias > d ? 0.0 : 1.0;
    }
    return s / 9.0;
  }`;

const _f = new THREE.Vector3(), _c = new THREE.Vector3();
export function makeSun(scene, sunDir, size = 4096) {
  const sun = new THREE.DirectionalLight(0xffffff, 1);
  sun.castShadow = true; sun.shadow.mapSize.set(size, size);
  const c = sun.shadow.camera; c.left = -1100; c.right = 1100; c.top = 1100; c.bottom = -1100; c.near = 10; c.far = 4000;
  sun.shadow.bias = 0; sun.shadow.normalBias = 0;
  const target = new THREE.Object3D(); scene.add(target); sun.target = target; scene.add(sun);
  const uniforms = { shadowMap: { value: null }, shadowMatrix: { value: sun.shadow.matrix }, shadowSize: { value: new THREE.Vector2(size, size) } };
  return {
    sun, uniforms,
    // range 'far' (flying): a 2.2 km box 450 m ahead; 'near' (on foot in the street): a 700 m box, three times sharper
    update(camera, range = 'far') {
      const half = range === 'near' ? 350 : 1100, ahead = range === 'near' ? 150 : 450;
      if (c.right !== half) { c.left = -half; c.right = half; c.top = half; c.bottom = -half; c.updateProjectionMatrix(); }
      // centre the box ahead of the camera, snapped to the texel grid so the shadows do not swim
      const f = _f; camera.getWorldDirection(f); f.y = 0; f.normalize();
      const centre = _c.copy(camera.position).addScaledVector(f, ahead); centre.y = 60;
      const snap = 2 * half / size * 4; centre.x = Math.round(centre.x / snap) * snap; centre.z = Math.round(centre.z / snap) * snap;
      target.position.copy(centre); sun.position.copy(centre).addScaledVector(sunDir, 2000);
      sun.updateMatrixWorld(); target.updateMatrixWorld();
      uniforms.shadowMap.value = sun.shadow.map ? sun.shadow.map.texture : null;
    },
  };
}
