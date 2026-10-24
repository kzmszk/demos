import * as THREE from 'three';

// A cloud layer: one huge disc at 1600 m with fbm coverage, lit from below by the low sun, drifting slowly.
// Drawn with depth write off so the city shows through its thin parts.

const vert = /* glsl */`
  varying vec3 vW;
  void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
const frag = /* glsl */`
  precision highp float;
  uniform float time; uniform vec3 sunDir; uniform vec3 sunCol; uniform vec3 skyCol; uniform vec3 fogCol; uniform vec3 camPos; uniform float fogDen;
  varying vec3 vW;
  float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
  float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int k=0;k<5;k++){ v += a*noise(p); p = p*2.07 + 3.7; a *= 0.5; } return v; }
  void main(){
    vec2 xy = vW.xz * 0.00045 + vec2(time * 0.004, 0.0);
    float c = fbm(xy); float d = fbm(xy * 3.1 + 9.0);
    float cover = smoothstep(0.48, 0.72, c + (d - 0.5) * 0.25);
    // thickness lights the underside: the low sun warms the edges, the dense middle stays grey-violet
    float thick = smoothstep(0.5, 0.95, c);
    vec3 lit = mix(vec3(1.05, 0.86, 0.72), vec3(0.58, 0.55, 0.62), thick);
    vec3 edge = vec3(1.3, 0.95, 0.72);
    vec3 col = mix(lit, edge, (1.0 - thick) * 0.5);
    vec3 V = vW - camPos; float dist = length(V);
    float horizon = smoothstep(0.0, 0.08, normalize(V).y);          // fade into the haze at the horizon
    float a = cover * horizon * (1.0 - exp(-dist * 0.00002)) * 0.95;
    col = mix(col, fogCol, 1.0 - exp(-fogDen * 0.35 * dist));
    gl_FragColor = vec4(col, a);
  }`;

export function makeClouds(scene, shared) {
  const uniforms = { time: { value: 0 }, sunDir: shared.sunDir, sunCol: shared.sunCol, skyCol: shared.skyCol, fogCol: shared.fogCol, camPos: shared.camPos, fogDen: shared.fogDen };
  const mat = new THREE.ShaderMaterial({ uniforms, vertexShader: vert, fragmentShader: frag, transparent: true, depthWrite: false, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(new THREE.CircleGeometry(40000, 48), mat);
  mesh.rotation.x = -Math.PI / 2; mesh.position.y = 1650; mesh.frustumCulled = false; mesh.renderOrder = 2; scene.add(mesh);
  return { mesh, update(t, cam) { uniforms.time.value = t; mesh.position.x = cam.x; mesh.position.z = cam.z; } };
}
