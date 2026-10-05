// film_page.js — evaluated in the viewer page by film.mjs: camera paths, frames stepped at a fixed rate, captions and
// titles drawn over each frame, and the sound rendered offline from the scene state the frames saw.
(() => {
  const V = window.VEN, THREE = V.THREE;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const smooth = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
  const F = window.FILM = { fps: 30, audLog: [], frame: 0 };

  // ---------------------------------------------------------------- paths
  // Catmull-Rom through the points, walked at constant speed (arc length)
  function curve(P) {
    if (P.length === 1) P = [P[0], P[0]];
    const Q = [P[0], ...P, P[P.length - 1]];
    const seg = (i, t) => { const [a, b, c, d] = [Q[i], Q[i + 1], Q[i + 2], Q[i + 3]], t2 = t * t, t3 = t2 * t;
      return b.map((_, k) => 0.5 * (2 * b[k] + (c[k] - a[k]) * t + (2 * a[k] - 5 * b[k] + 4 * c[k] - d[k]) * t2 + (3 * b[k] - a[k] - 3 * c[k] + d[k]) * t3)); };
    const S = []; let L = 0, prev = null;
    for (let i = 0; i < P.length - 1; i++) for (let k = 0; k <= 48; k++) {
      if (i > 0 && k === 0) continue;
      const q = seg(i, k / 48); if (prev) L += Math.hypot(...q.map((v, j) => v - prev[j])); S.push([L, q]); prev = q;
    }
    return { len: L, at(u) {
      const s = clamp(u, 0, 1) * L; let lo = 0, hi = S.length - 1;
      while (hi - lo > 1) { const m = (lo + hi) >> 1; if (S[m][0] < s) lo = m; else hi = m; }
      const [s0, a] = S[lo], [s1, b] = S[hi], f = s1 > s0 ? (s - s0) / (s1 - s0) : 0;
      return a.map((v, j) => v + (b[j] - v) * f);
    } };
  }
  // keys [[u, value], ...] -> value at u, eased between keys
  function keys(K, def) {
    if (K === undefined) return () => def;
    if (typeof K === 'number') return () => K;
    return (u) => {
      if (u <= K[0][0]) return K[0][1];
      for (let i = 0; i < K.length - 1; i++) if (u <= K[i + 1][0]) { const f = (u - K[i][0]) / (K[i + 1][0] - K[i][0]); return K[i][1] + (K[i + 1][1] - K[i][1]) * smooth(f); }
      return K[K.length - 1][1];
    };
  }
  const ease = (e) => (e === 'inout' ? (u) => smooth(u) : e === 'out' ? (u) => 1 - (1 - u) * (1 - u) : (u) => u);

  // a shot: the camera at u = 0..1 (pose) and what the sound should hear; S.dur seconds
  function makeShot(S) {
    const cam = V.camera, E = ease(S.ease);
    if (S.kind === 'walk') {
      const C = curve(S.path), pitch = keys(S.pitch, 0.02), yawK = S.yaw === undefined ? null : keys(S.yaw), eye = S.eye || 1.62, LA = S.lookAt ? curve(S.lookAt) : null;
      let wz = null, bob = 0, last = null;
      return {
        len: C.len,
        pose(u, dt) {
          const w = E(u), p = C.at(w), ahead = C.at(Math.min(1, w + 2.0 / Math.max(2, C.len))), back = C.at(Math.max(0, w - 0.5 / Math.max(2, C.len)));
          const yaw = yawK ? yawK(u) : Math.atan2(ahead[1] - back[1], ahead[0] - back[0]) + (S.yawOff || 0);
          const s = V.tiles.sample(p[0], p[1]); const z = s.z != null ? s.z : (wz ?? 1.1);
          if (wz === null || dt <= 0) wz = z; else wz += (z - wz) * Math.min(1, dt * 12);
          const v = last && dt > 0 ? Math.hypot(p[0] - last[0], p[1] - last[1]) / dt : 0;
          if (dt > 0) { bob += dt * v * 1.15 * Math.PI; V.controls.vel.set((p[0] - last[0]) / dt, (p[1] - last[1]) / dt, 0); } else V.controls.vel.set(0, 0, 0);
          last = p;
          cam.position.set(p[0], p[1], wz + eye + Math.sin(bob * 2) * 0.012 * Math.min(1, v / 1.4));
          cam.up.set(0, 0, 1);
          if (LA) { const q = LA.at(w); cam.lookAt(q[0], q[1], q[2] + pitch(u) * 0); return; }
          const pt = pitch(u);
          cam.lookAt(cam.position.x + Math.cos(yaw) * Math.cos(pt), cam.position.y + Math.sin(yaw) * Math.cos(pt), cam.position.z + Math.sin(pt));
        },
        at: (u) => C.at(E(u)),
      };
    }
    if (S.kind === 'fly') {
      const C = curve(S.path), T = S.look ? curve(S.look) : null, yawK = S.yaw === undefined ? null : keys(S.yaw), pitch = keys(S.pitch, -0.3);
      return {
        len: C.len,
        pose(u) {
          const w = E(u), p = C.at(w); cam.position.set(p[0], p[1], p[2]); cam.up.set(0, 0, 1);
          if (T) { const q = T.at(w); cam.lookAt(q[0], q[1], q[2]); }
          else { const y = yawK(u), pt = pitch(u); cam.lookAt(p[0] + Math.cos(y) * Math.cos(pt), p[1] + Math.sin(y) * Math.cos(pt), p[2] + Math.sin(pt)); }
          V.controls.vel.set(0, 0, 0);
        },
        at: (u) => C.at(E(u)),
      };
    }
    if (S.kind === 'boat') {
      const yaw = keys(S.yaw, 0), pitch = keys(S.pitch, -0.05);
      return {
        len: S.speed * S.dur,
        pose(u) { V.ride.seatPose(cam, yaw(u), pitch(u)); V.controls.vel.set(0, 0, 0); },
        at: () => [V.ride.pos.x, V.ride.pos.y],
      };
    }
    throw new Error('shot kind ' + S.kind);
  }

  // ---------------------------------------------------------------- the view is complete: tiles, near detail, pipelines
  async function complete(maxMs = 20000) {
    const t0 = performance.now();
    for (;;) {
      V.tiles.update(V.camera);
      const n = V.tiles.pending(V.camera.position) + V.pipes.pending;
      if (!n) return true;
      if (performance.now() - t0 > maxMs) return false;
      await sleep(15);
    }
  }

  // ---------------------------------------------------------------- shots
  let cur = null, shotT = 0, shotSpec = null;
  F.begin = async (o = {}) => {
    F.fps = o.fps || 30;
    if (V.app.mode === 'title') V.ui.start('walk');
    V.stopLoop();
    V.controls.enabled = false;
    V.tiles.chunkMs = 400;                       // a detailed facade chunk in one frame: nothing pops in mid-shot
    document.querySelectorAll('.ui, #veil').forEach((e) => (e.style.display = 'none'));
    return true;
  };
  F.shot = async (S) => {
    shotSpec = S;
    if (!!V.app.night !== !!S.night) await V.night(!!S.night);
    V.app.bright = S.bright || 1;
    if (S.kind === 'boat') { V.app.setRoute(S.route); V.ride.setRoute(S.route, S.s0); V.ride.speed = S.speed; }
    else V.app.setMode(S.kind === 'walk' ? 'walk' : 'fly');
    V.controls.enabled = false;
    cur = makeShot(S); shotT = 0;
    // stream in what the path will see
    const n = Math.max(2, Math.ceil((cur.len || 1) / 25));
    let ok = true;
    for (let i = 0; i <= n; i++) {
      const u = i / n;
      if (S.kind === 'boat') { V.ride.setRoute(S.route, S.s0 + S.speed * S.dur * u); V.ride.speed = 0; V.step(0, 0, () => cur.pose(u, 0), true); }
      else cur.pose(u, 0);
      ok = (await complete()) && ok;
    }
    if (S.kind === 'boat') { V.ride.setRoute(S.route, S.s0); V.ride.speed = S.speed; }
    // settle at the first frame: eye adaptation at once, then a few frames for the temporal AA history
    for (let i = 0; i < 3; i++) { V.step(0, 0, () => cur.pose(0, 0), true); await complete(); }
    for (let i = 0; i < 12; i++) { V.step(0, 0, () => cur.pose(0, 0), false); V.pipeline.render(); }
    cur.pose(0, 0);
    return { ok, len: +cur.len.toFixed(1) };
  };
  // one frame of the current shot: step by 1/fps, make the view complete, draw, overlay, return a JPEG (base64)
  F.next = async (q = 0.93) => {
    const dt = 1 / F.fps, u = clamp(shotT / shotSpec.dur, 0, 1);
    V.step(dt, dt, (d) => cur.pose(u, d), false);
    await complete(8000);
    F.audLog.push({ ...V.aud });
    const c = await V.frameCanvas();
    overlay(c, shotT, shotSpec);
    shotT += dt; F.frame++;
    return c.toDataURL('image/jpeg', q).split(',')[1];
  };
  // a still of the shot at u (scouting): no time passes
  F.still = async (u, q = 0.9) => {
    V.ride.speed = 0;
    if (shotSpec.kind === 'boat') V.ride.setRoute(shotSpec.route, shotSpec.s0 + shotSpec.speed * shotSpec.dur * u);
    for (let i = 0; i < 2; i++) { V.step(0, 0, (d) => cur.pose(u, d), true); await complete(); }
    for (let i = 0; i < 8; i++) { V.step(0, 0, (d) => cur.pose(u, d), false); V.pipeline.render(); }
    const c = await V.frameCanvas(); overlay(c, u * shotSpec.dur, shotSpec);
    return c.toDataURL('image/jpeg', q).split(',')[1];
  };

  // ---------------------------------------------------------------- titles and captions (the app's own type)
  const INK = '246, 241, 231';
  const SANS = '"Helvetica Neue", Helvetica, Arial, "Noto Sans CJK JP", "Noto Sans JP", sans-serif';
  const JP = '"Noto Sans CJK JP", "Noto Sans JP", "Hiragino Sans", sans-serif';
  function fade(t, a, b, fin, fout) { return clamp(Math.min((t - a) / fin, (b - t) / fout), 0, 1); }
  function overlay(c, t, S) {
    const g = c.getContext('2d'), W = c.width, H = c.height, k = H / 1080;
    if (S.title) {
      const a = fade(t, S.title.in, S.title.out, S.title.fin || 1.2, S.title.fout || 1.0);
      if (a > 0) {
        g.save();
        const gr = g.createLinearGradient(0, H * 0.35, 0, H); gr.addColorStop(0, 'rgba(8,10,14,0)'); gr.addColorStop(1, `rgba(8,10,14,${0.55 * a})`);
        g.fillStyle = gr; g.fillRect(0, 0, W, H);
        const fs = Math.min(0.23 * W, 0.4 * H);
        g.font = `700 ${fs}px ${SANS}`; g.letterSpacing = `${-0.055 * fs}px`; g.textBaseline = 'alphabetic';
        const x0 = 0.04 * W - 0.06 * fs, base = H - 0.06 * H - (S.title.sub ? 120 * k : 40 * k);
        if (S.title.blend === 'normal') { g.fillStyle = `rgba(${INK}, ${0.88 * a})`; g.fillText('VENEZIA', x0, base); }
        else { g.globalCompositeOperation = 'soft-light'; g.fillStyle = `rgba(${INK}, ${0.92 * a})`; g.fillText('VENEZIA', x0, base); g.fillText('VENEZIA', x0, base); }   // soft light: twice, once is faint
        g.globalCompositeOperation = 'source-over';
        if (S.title.sub) {
          g.font = `400 ${26 * k}px ${JP}`; g.letterSpacing = `${0.08 * 26 * k}px`; g.fillStyle = `rgba(${INK}, ${0.78 * a})`;
          g.fillText(S.title.sub, 0.04 * W + 4 * k, base + 74 * k);
        }
        if (S.title.url) {
          g.font = `400 ${24 * k}px ${SANS}`; g.letterSpacing = `${0.1 * 24 * k}px`; g.fillStyle = `rgba(${INK}, ${0.9 * a})`;
          g.fillText(S.title.url, 0.04 * W + 4 * k, base + 74 * k + (S.title.sub ? 46 * k : 0));
        }
        g.restore();
      }
    }
    if (S.cap) {
      const a = fade(t, 0.35, S.dur - 0.25, 0.6, 0.45);
      if (a > 0) {
        g.save();
        const gr = g.createLinearGradient(0, H - 260 * k, 0, H); gr.addColorStop(0, 'rgba(8,10,14,0)'); gr.addColorStop(1, `rgba(8,10,14,${0.38 * a})`);
        g.fillStyle = gr; g.fillRect(0, H - 260 * k, W, 260 * k);
        g.shadowColor = 'rgba(0,0,0,0.35)'; g.shadowBlur = 12 * k;
        g.font = `500 ${34 * k}px ${JP}`; g.letterSpacing = `${0.06 * 34 * k}px`; g.fillStyle = `rgba(${INK}, ${0.96 * a})`; g.textBaseline = 'alphabetic';
        g.fillText(S.cap.ja, 72 * k, H - 96 * k);
        g.font = `400 ${16 * k}px ${SANS}`; g.letterSpacing = `${0.22 * 16 * k}px`; g.fillStyle = `rgba(${INK}, ${0.7 * a})`;
        g.fillText(S.cap.en.toUpperCase(), 74 * k, H - 62 * k);
        g.restore();
      }
    }
    if (S.black) {        // fade to (or from) black: [t0, t1, from, to]
      const [t0, t1, a0, a1] = S.black, f = clamp((t - t0) / (t1 - t0), 0, 1), a = a0 + (a1 - a0) * smooth(f);
      if (a > 0) { g.fillStyle = `rgba(0,0,0,${a})`; g.fillRect(0, 0, W, H); }
    }
  }

  // ---------------------------------------------------------------- sound, rendered offline
  // what: 'amb' (the natural sounds the frames heard, F.audLog at fps) or 'music' (the given piece, sec seconds).
  // Returns the number of 4 MB base64 chunks of a 16-bit WAV (F.chunk(i) hands them out).
  let wav = null;
  F.sound = async (what, o = {}) => {
    const rate = 48000, sec = what === 'amb' ? F.audLog.length / F.fps + (o.tail || 4) : o.sec;
    const oac = new OfflineAudioContext(2, Math.ceil(sec * rate), rate);
    const A = V.createAudio({ context: oac, debug: true, noMusic: what === 'amb', noAmb: what === 'music' });
    await A.start();
    for (let i = 0; i < 2400; i++) { const k = A.info().kit.split('/'); if (+k[1] > 0 && k[0] === k[1]) break; await sleep(50); }
    await sleep(600);                            // the rooms' impulse responses are made a moment after start
    const m = A._dbg.master.gain; m.cancelScheduledValues(0); m.value = 1;
    if (what === 'amb') {
      const N = F.audLog.length;
      for (let i = 0; i < N; i++) oac.suspend(i / F.fps).then(() => { A.update(1 / F.fps, F.audLog[i]); oac.resume(); });
    } else {
      const s = { mode: o.mode || 'title', interior: null, night: false, walkSpeed: 0, boatPhase: -1, boatSpeed: 0, water: 0, piazza: 0, camZ: 2 };
      for (let i = 0; i * 0.25 < sec - 0.5; i++) oac.suspend(i * 0.25).then(() => { A.update(0.25, s); oac.resume(); });
    }
    const buf = await oac.startRendering();
    // 16-bit PCM WAV
    const n = buf.length, ch = [buf.getChannelData(0), buf.getChannelData(1)], out = new DataView(new ArrayBuffer(44 + n * 4));
    const str = (o2, s2) => { for (let i = 0; i < s2.length; i++) out.setUint8(o2 + i, s2.charCodeAt(i)); };
    str(0, 'RIFF'); out.setUint32(4, 36 + n * 4, true); str(8, 'WAVEfmt '); out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, 2, true);
    out.setUint32(24, rate, true); out.setUint32(28, rate * 4, true); out.setUint16(32, 4, true); out.setUint16(34, 16, true); str(36, 'data'); out.setUint32(40, n * 4, true);
    for (let i = 0, p = 44; i < n; i++) for (let c2 = 0; c2 < 2; c2++, p += 2) out.setInt16(p, clamp(Math.round(ch[c2][i] * 32767), -32768, 32767), true);
    const bytes = new Uint8Array(out.buffer); let b64 = '';
    for (let i = 0; i < bytes.length; i += 0x8000) b64 += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    wav = btoa(b64);
    return Math.ceil(wav.length / 4e6);
  };
  F.chunk = (i) => wav.slice(i * 4e6, (i + 1) * 4e6);
  // the middle of the walkable strip across each point of a path (perpendicular to it, within half m): for paths down calli
  F.center = (P, half = 4) => P.map((p, i) => {
    const a = P[Math.max(0, i - 1)], b = P[Math.min(P.length - 1, i + 1)], L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    const nx = -(b[1] - a[1]) / L, ny = (b[0] - a[0]) / L, ok = (d) => V.tiles.sample(p[0] + nx * d, p[1] + ny * d).z != null;
    let c = null; for (let d = 0; d <= half && c === null; d += 0.1) { if (ok(d)) c = d; else if (ok(-d)) c = -d; }
    if (c === null) return { p, w: 0 };
    let hi = c, lo = c; while (hi - c < half && ok(hi + 0.1)) hi += 0.1; while (c - lo < half && ok(lo - 0.1)) lo -= 0.1;
    const m = (hi + lo) / 2; return { p: [+(p[0] + nx * m).toFixed(2), +(p[1] + ny * m).toFixed(2)], w: +(hi - lo).toFixed(2) };
  });
  // the bar lines of a piece (seconds from its start), for cutting on the music
  F.bars = (name, pass = 0, n = 40) => { const sc = V.scores()[name][pass], out = []; for (let b = 0; b <= n; b++) out.push(sc.T(b * sc.bpb)); return { bars: out, len: sc.len }; };
})();
