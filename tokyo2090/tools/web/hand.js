import * as THREE from 'three';

// Flying hand in hand. When you take Saki's hand she flies for both of you: a gentle autopilot that keeps clear of
// the buildings, drifts toward rising air and holds a comfortable speed, so you can look at her instead of the sky.

const clamp = THREE.MathUtils.clamp;

export function makeAutopilot(roof, ground) {
  let want = 0, settle = 0, roll = 0, pitch = 0, flareOn = false;
  return {
    // writes f.input for this frame
    step(f, dt) {
      const [x, y] = f.dataXY(); const z = f.p.y, s = f.speed;
      let best = 0, bestScore = -1e9, straightClear = 0;
      for (let off = -1.3; off <= 1.31; off += 0.13) {
        const h = f.heading + off; let clear = 1e9, lift = 0;
        for (const d of [12, 25, 45, 70, 100, 140, 190]) {
          const px = x + Math.sin(h) * d, py = y + Math.cos(h) * d;
          const top = roof.top(px, py), g = ground(px, py);
          clear = Math.min(clear, z - d * 0.1 - Math.max(top, g));         // the path sinks about 1 in 10
        }
        lift = f.windUp(x + Math.sin(h) * 30, y + Math.cos(h) * 30, z) + 0.6 * f.windUp(x + Math.sin(h) * 70, y + Math.cos(h) * 70, z);
        const alt = z - ground(x, y);
        let score = Math.min(clear, 70) * 1.2 + lift * (alt < 90 ? 7 : 3) - Math.abs(off) * 12;
        if (clear < 12) score -= 300;
        if (Math.abs(off) < 0.07) straightClear = clear;
        if (score > bestScore) { bestScore = score; best = off; }
      }
      // steer gently; hold a new heading for a moment so she does not hunt
      // the wanted bank drifts toward the best heading; it never steps (a step every 0.6 s read as a jolt beside her)
      want += (best - want) * Math.min(1, dt * (Math.abs(best) > 0.9 ? 4 : 0.8));
      const urgent = straightClear < 25;
      // ease toward the wanted bank: a step here was a visible jolt beside her
      const rollWant = clamp(want * (urgent ? 1.6 : 1.0), urgent ? -1 : -0.45, urgent ? 1 : 0.45);
      roll += (rollWant - roll) * Math.min(1, dt * (urgent ? 6 : 1.0)); f.input.roll = roll;
      // speed: a slow, easy glide at ~14 m/s; climb when the air lifts
      const lift = f.updraft;
      // smooth, with hysteresis: toggling the cape and stepping the pitch made the glide bob about once a second
      if (!flareOn && lift > 4.0 && s > 12.5) flareOn = true; else if (flareOn && (lift < 2.5 || s < 11.5)) flareOn = false;
      const pitchWant = straightClear < 10 ? 1 : clamp((s - 14) * 0.3, -0.5, 0.5) + (lift > 3 ? 0.2 : 0);
      pitch += (pitchWant - pitch) * Math.min(1, dt * (straightClear < 10 ? 8 : 1.2)); f.input.pitch = pitch;
      f.input.flare = flareOn;
      f.input.tuck = false;
    },
  };
}

export const HAND_LINES_UNUSED = ['……手、あったかい。', 'こっち見て。', 'ね。わたしが飛ぶから、見てて。', 'ずっと、こうしてたいね。', '風、気持ちいい。', '落ちないよ。わたしがいる。', '……なに。顔、見すぎ。', 'あの屋上まで、いっしょに。'];
