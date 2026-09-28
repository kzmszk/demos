// The tool's shadow, worked out analytically instead of through the shadow map.
//
// A pencil a few centimetres above the paper, under a lamp whose bulb is a few centimetres across, casts a
// shadow that is sharp where the point touches the page and goes soft and pale towards the far end. A shadow
// map blurs everything by the same amount, so the tools don't cast into it; instead every receiving surface
// asks, for the key light only, how much of the bulb the tool hides: the tool is a tapered rod (a segment
// with a radius profile), the bulb a disc of sixteen points, each ray tested against the rod with a soft edge
// so the samples blend. No noise, nothing to filter, and cheap: most fragments leave after one test.
import * as THREE from 'three';

export const TOOL_UNIFORMS = {
  uToolA: { value: new THREE.Vector3() }, // the tip, view space
  uToolU: { value: new THREE.Vector3(0, 1, 0) }, // unit vector up the tool, view space
  uToolL: { value: 0 }, // length (0: no tool out)
  uToolS: { value: new THREE.Vector4() }, // radius profile: positions along the tool...
  uToolR: { value: new THREE.Vector4() }, // ...and the radius at each
  uLampR: { value: 2.4 }, // the bulb's radius
};

const GLSL = /* glsl */ `
uniform vec3 uToolA;
uniform vec3 uToolU;
uniform float uToolL;
uniform vec4 uToolS;
uniform vec4 uToolR;
uniform float uLampR;

float toolRad( float s ) {
  float r = mix( uToolR.x, uToolR.y, clamp( ( s - uToolS.x ) / max( 1e-4, uToolS.y - uToolS.x ), 0.0, 1.0 ) );
  r = mix( r, uToolR.z, clamp( ( s - uToolS.y ) / max( 1e-4, uToolS.z - uToolS.y ), 0.0, 1.0 ) );
  return mix( r, uToolR.w, clamp( ( s - uToolS.z ) / max( 1e-4, uToolS.w - uToolS.z ), 0.0, 1.0 ) );
}

// closest approach of P + V t (t in [0, 1]) to the tool's axis uToolA + uToolU s (s in [0, uToolL]) -> (distance, t, s)
vec3 toolClosest( vec3 P, vec3 V ) {
  vec3 r = P - uToolA;
  float a = dot( V, V ), b = dot( V, uToolU ), c = dot( V, r ), f = dot( uToolU, r );
  float den = a - b * b;
  float t = den > 1e-6 * a ? clamp( ( b * f - c ) / den, 0.0, 1.0 ) : 0.0;
  float s = b * t + f;
  if ( s < 0.0 ) { s = 0.0; t = clamp( - c / a, 0.0, 1.0 ); }
  else if ( s > uToolL ) { s = uToolL; t = clamp( ( b * uToolL - c ) / a, 0.0, 1.0 ); }
  return vec3( length( P + V * t - uToolA - uToolU * s ), t, s );
}

// fraction of the bulb (centred at Lc) that P can see past the tool
float toolShadow( vec3 P, vec3 Lc ) {
  if ( uToolL <= 0.0 ) return 1.0;
  vec3 V = Lc - P;
  vec3 q = toolClosest( P, V );
  if ( q.x > max( uToolR.z, uToolR.w ) + uLampR * min( 1.0, q.y * 1.3 + 0.05 ) + 0.05 ) return 1.0;
  vec3 w = normalize( V );
  vec3 t1 = normalize( cross( w, abs( w.y ) < 0.9 ? vec3( 0.0, 1.0, 0.0 ) : vec3( 1.0, 0.0, 0.0 ) ) );
  vec3 t2 = cross( w, t1 );
  float occ = 0.0;
  for ( int k = 0; k < 16; k ++ ) {
    float rr = sqrt( ( float( k ) + 0.5 ) / 16.0 ) * uLampR;
    float th = float( k ) * 2.39996323;
    vec3 qi = toolClosest( P, V + ( t1 * cos( th ) + t2 * sin( th ) ) * rr );
    // soften each sample's edge by about half the spacing between samples, as it lands on P
    float h = 0.2 * uLampR * qi.y + 0.004;
    float rad = toolRad( qi.z );
    occ += 1.0 - smoothstep( rad - h, rad + h, qi.x );
  }
  return 1.0 - occ / 16.0;
}
`;

const SPOT_SHADOW = 'directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ]';

// the lights chunk, with the key light (the only spot that casts shadows) also dimmed by the tool
function lightsChunk() {
  const src = THREE.ShaderChunk.lights_fragment_begin;
  const at = src.indexOf(SPOT_SHADOW);
  if (at < 0) throw new Error('toolshadow: lights chunk changed');
  const end = src.indexOf('\n', at);
  return src.slice(0, end + 1) + '\t\tdirectLight.color *= toolShadow( geometryPosition, spotLight.position );\n' + src.slice(end + 1);
}

export function withToolShadow(mat) {
  const prev = mat.onBeforeCompile;
  const prevKey = mat.customProgramCacheKey();
  mat.onBeforeCompile = (sh, r) => {
    prev.call(mat, sh, r);
    Object.assign(sh.uniforms, TOOL_UNIFORMS);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <lights_pars_begin>', '#include <lights_pars_begin>\n' + GLSL)
      .replace('#include <lights_fragment_begin>', lightsChunk());
  };
  mat.customProgramCacheKey = () => prevKey + '|toolshadow';
  mat.needsUpdate = true;
}

// radius profiles, [s0..s3] along the tool from its point and the radius there
const PROFILES = {
  pencil: [[0, 0.34, 2.09, 12.44], [0.03, 0.08, 0.35, 0.36]],
  pen: [[0, 1.1, 2.5, 13.6], [0.03, 0.2, 0.42, 0.5]],
  brush: [[0, 1.0, 3.8, 18.8], [0.02, 0.3, 0.34, 0.16]],
};

const _a = new THREE.Vector3(), _u = new THREE.Vector3();

// once per frame, after the tool is posed and the camera's matrices are current
export function updateToolShadow(tools, camera) {
  const U = TOOL_UNIFORMS;
  const t = tools.pencil.visible ? tools.pencil : tools.pen.visible ? tools.pen : tools.brush.visible ? tools.brush : null;
  if (!t) { U.uToolL.value = 0; return; }
  const kind = t === tools.pencil ? 'pencil' : t === tools.pen ? 'pen' : 'brush';
  _a.copy(t.position);
  _u.set(0, 1, 0).applyQuaternion(t.quaternion);
  U.uToolA.value.copy(_a).applyMatrix4(camera.matrixWorldInverse);
  U.uToolU.value.copy(_u).transformDirection(camera.matrixWorldInverse);
  const [s, r] = PROFILES[kind];
  U.uToolS.value.set(s[0], s[1], s[2], s[3]);
  U.uToolR.value.set(r[0], r[1], r[2], r[3]);
  U.uToolL.value = t.userData.length;
}
