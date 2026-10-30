// node --test shared/exposure/exposure.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { exposureBoost, adapt, meanLog } from './meter.js';

const near = (a, b, e = 1e-9) => assert.ok(Math.abs(a - b) <= e, `${a} ≉ ${b}`);
const P = { target: -5, strength: 0.85, max: 32 };

test('a frame at or above the target keeps its exposure; no reading yet keeps it too', () => {
  assert.equal(exposureBoost(-3.6, 1, P), 1);          // an open street
  assert.equal(exposureBoost(-5, 1, P), 1);
  assert.equal(exposureBoost(null, 1, P), 1);
  assert.equal(exposureBoost(-8, 0, P), 1);
});

test('a dark frame is lifted part of the way, in stops, after the exposure already given', () => {
  // the hall: −8.3 metered at exposure 1.02 → 3.3 stops short → 0.85 × 3.3 stops up
  near(exposureBoost(-8.3, 1.02, P), Math.pow(2, 0.85 * (-5 - (-8.3 + Math.log2(1.02)))));
  // the same light at twice the exposure is lifted a stop × strength less
  near(exposureBoost(-8, 2, P) * Math.pow(2, 0.85), exposureBoost(-8, 1, P));
  // brighter screens (the brightness slider) leave less to lift
  assert.ok(exposureBoost(-8, 2, P) < exposureBoost(-8, 1, P));
});

test('the lift is capped', () => {
  assert.equal(exposureBoost(-16, 1, P), 32);
  assert.equal(exposureBoost(-16, 1, { ...P, max: 10 }), 10);
});

test('adapt eases in stops, opening slower than closing, and arrives at once with a long step', () => {
  near(adapt(1, 8, 0.5, { up: 1, down: 2 }), Math.pow(2, 1.5));     // 3 stops × 0.5
  near(adapt(8, 1, 0.25, { up: 1, down: 2 }), Math.pow(2, 1.5));    // 3 stops × 0.5, down
  near(adapt(1, 8, 10), 8);
  near(adapt(4, 4, 0.1), 4);
});

test('meanLog reads the 8-bit log2 luminance back (−16 … +4) and weights the centre', () => {
  const w = 8, h = 4, px = new Uint8Array(w * h * 4);
  px.fill(0); assert.equal(meanLog(px, w, h), -16);
  for (let i = 0; i < px.length; i += 4) px[i] = 255;
  near(meanLog(px, w, h), 4);
  for (let i = 0; i < px.length; i += 4) px[i] = 204;   // 0.8 → −16 + 16 = 0
  near(meanLog(px, w, h), 0);
  // bright centre, dark rim: above the plain mean
  px.fill(0);
  for (let y = 1; y < 3; y++) for (let x = 3; x < 5; x++) px[(y * w + x) * 4] = 255;
  assert.ok(meanLog(px, w, h) > -16 + 20 * (4 / 32));
  // a padded row stride
  const s = 64, q = new Uint8Array(s * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) q[y * s + x * 4] = 204;
  near(meanLog(q, w, h, s), 0);
});
