// shared/exposure — metered eye adaptation for the city demos.
// The cities set their exposure from where the camera is (open street, under a roof, inside a hall).  That guess knows
// nothing of the light actually reaching the eye, so a hall, a torii tunnel or a shaded canal could still end up almost
// black: on a bright desktop monitor it reads, on a MacBook or a phone it does not.  The meter looks at the frame
// itself — the scene-linear colour before exposure and tone mapping — and lifts the exposure when it is too dark.
// It never darkens: where the old exposure was fine (the meter reads at or above the target) nothing changes.
//
//   const meter = createMeter({ THREE, tsl, renderer, source: scenePass });   // the pass with the scene-linear colour
//   pipeline.outputNode = meter.wrap(pipeline.outputNode);                    // so the pipeline draws the meter too
//   meter.update();                                     // once a frame, after pipeline.render()
//   boost = adapt(boost, exposureBoost(meter.logLum, expo), dt);              // then exposure = expo · boost
//
// The readback is asynchronous and a few frames late, which is what an eye does anyway.  The three namespaces come
// from the city's bundle (shared/ has no three of its own).

// log2 luminance is stored in 8 bits over this range (a 0.08 stop step: plenty for a meter)
const LO = -16, HI = 4;
const W = 64, H = 36;          // 64 px × 4 bytes = 256 bytes a row: no row padding on readback

// The boost (≥ 1) that brings the metered, exposed log2 luminance up toward `target`.  strength < 1 leaves a dark place
// darker than a bright one (it still reads as shade), max caps it (a black screen stays black, not noise).
export function exposureBoost(logLum, expo, { target = -5, strength = 0.85, max = 32 } = {}) {
  if (logLum == null || !(expo > 0)) return 1;
  const short = target - (logLum + Math.log2(expo));
  return short <= 0 ? 1 : Math.min(max, Math.pow(2, strength * short));
}

// eases a boost toward its target in stops: rate per second; brightening (eyes opening) a little slower than darkening
export function adapt(cur, want, dt, { up = 1.2, down = 2.5 } = {}) {
  const a = Math.log2(cur), b = Math.log2(want), r = b > a ? up : down;
  return Math.pow(2, a + (b - a) * Math.min(1, dt * r));
}

// centre-weighted mean of the stored log2 luminance (the centre counts three times the corners)
export function meanLog(px, w = W, h = H, stride = w * 4) {
  let s = 0, n = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const dx = (x + 0.5) / w - 0.5, dy = ((y + 0.5) / h - 0.5) * 0.75;
    const k = 1 + 2 * Math.exp(-(dx * dx + dy * dy) / 0.06);
    s += k * (LO + (px[y * stride + x * 4] / 255) * (HI - LO)); n += k;
  }
  return s / n;
}

export function createMeter({ THREE, tsl, renderer, source, interval = 0.15 }) {
  const { Fn, uv, vec2, vec3, vec4, float, dot, log2, max, rtt } = tsl;
  const src = source.getTextureNode('output');
  const cell = vec2(1 / W, 1 / H);
  // four taps a cell, each to log2 luminance, averaged (a log mean: one bright lamp does not set the exposure)
  const logLum = Fn(() => {
    let s = float(0);
    for (const [ox, oy] of [[-0.25, -0.25], [0.25, -0.25], [-0.25, 0.25], [0.25, 0.25]]) {
      const c = src.sample(uv().add(cell.mul(vec2(ox, oy)))).rgb;
      s = s.add(log2(max(dot(c, vec3(0.2126, 0.7152, 0.0722)), float(Math.pow(2, LO)))));
    }
    const e = s.mul(0.25).sub(LO).div(HI - LO).clamp(0, 1);
    return vec4(e, e, e, 1);
  })();
  // drawn inside the pipeline (a material of its own cannot see the pass's texture), and only when a reading is due
  const small = rtt(logLum, W, H, { type: THREE.UnsignedByteType, depthBuffer: false, autoUpdate: false });
  small.renderTarget.texture.colorSpace = THREE.NoColorSpace;
  small.textureNeedsUpdate = false;
  let busy = false, drawn = false, last = -Infinity;
  const meter = {
    logLum: null,            // centre-weighted mean log2 luminance of the last metered frame, before exposure
    // the pipeline's output node, made to depend on the small target (so the pipeline draws it); the picture is unchanged
    wrap: (node) => node.add(small.sample(vec2(0.5, 0.5)).mul(0)),
    // once a frame, after pipeline.render(): asks for a drawing every `interval` seconds and reads the last one back
    update(now = performance.now() / 1000) {
      if (drawn) {
        drawn = false; busy = true;
        renderer.readRenderTargetPixelsAsync(small.renderTarget, 0, 0, W, H)
          .then((px) => { meter.logLum = meanLog(px, W, H, Math.floor(px.length / H)); })
          .catch(() => {})
          .finally(() => { busy = false; });
      } else if (!busy && !small.textureNeedsUpdate && now - last >= interval) {
        last = now; small.textureNeedsUpdate = true; drawn = true;
      }
    },
  };
  return meter;
}
