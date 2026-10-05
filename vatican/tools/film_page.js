// film_page.js — evaluated in the VATICANO page by film.mjs: shots taken from the drone tour (or flown on a path),
// frames stepped at a fixed rate, the tour's captions drawn over them in the page's own type, and the sound rendered
// offline (the score, the fountains and the bells of the square).
(() => {
  const V = window.VAT, THREE = V.THREE;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const smooth = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
  const F = window.FILM = { fps: 30, camLog: [], frame: 0 };

  // ---------------------------------------------------------------- the tour's camera (tour.js poseAt, here for any time)
  function cr(P0, P1, P2, P3, u) {
    const out = [0, 0, 0];
    for (let k = 0; k < 3; k++) { const p0 = P0[k], p1 = P1[k], p2 = P2[k], p3 = P3[k]; out[k] = 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u * u * u); }
    return out;
  }
  function poseAt(seg, t) {
    const K = seg.keys, n = K.length;
    let i = 0; while (i < n - 2 && t > K[i + 1][0]) i++;
    const k0 = K[Math.max(0, i - 1)], k1 = K[i], k2 = K[i + 1], k3 = K[Math.min(n - 1, i + 2)];
    let u = clamp((t - k1[0]) / (k2[0] - k1[0]), 0, 1);
    if (i === 0 && seg.cut) u = u * u * (3 - 2 * u) * 0.35 + u * 0.65;
    const ext = (a, b) => [2 * a[0] - b[0], 2 * a[1] - b[1], 2 * a[2] - b[2]];
    const P0 = i === 0 ? ext(k1[1], k2[1]) : k0[1], L0 = i === 0 ? ext(k1[2], k2[2]) : k0[2];
    const P3 = i + 2 >= n ? ext(k2[1], k1[1]) : k3[1], L3 = i + 2 >= n ? ext(k2[2], k1[2]) : k3[2];
    return { p: cr(P0, k1[1], k2[1], P3, u), l: cr(L0, k1[2], k2[2], L3, u) };
  }
  const ease = (e) => (e === 'inout' ? smooth : e === 'out' ? (u) => 1 - (1 - u) * (1 - u) : e === 'in' ? (u) => u * u : (u) => u);
  function makeShot(S) {
    const cam = V.camera, E = ease(S.ease);
    if (S.kind === 'tour') {
      const seg = V.tour.segments.find((s) => s.id === S.seg);
      if (!seg) throw new Error('no tour segment ' + S.seg);
      return { zone: seg.zone, pose(u) { const q = poseAt(seg, S.a + (S.b - S.a) * E(u)); cam.position.set(...q.p); cam.up.set(0, 0, 1); cam.lookAt(...q.l); } };
    }
    throw new Error('shot kind ' + S.kind);
  }

  // ---------------------------------------------------------------- the view is complete: zones and artworks in
  // (every texture goes through three's default loading manager: count what it still has in flight)
  const M = THREE.DefaultLoadingManager; let inFlight = 0;
  const wrap = (k, d) => { const f = M[k].bind(M); M[k] = (...a) => { inFlight = Math.max(0, inFlight + d); return f(...a); }; };
  wrap('itemStart', 1); wrap('itemEnd', -1); wrap('itemError', 0);
  function texturesReady() {
    if (inFlight > 0) return false;
    let ok = true;
    V.scene.traverse((o) => { if (!o.isMesh || !o.visible || !o.material || !o.material.map) return; const im = o.material.map.image; if (!im || (im.complete === false) || (im.naturalWidth === 0)) ok = false; });
    return ok;
  }
  F.pending = () => ({ inFlight, ready: texturesReady() });
  async function complete(maxMs = 20000) {
    const t0 = performance.now();
    while (!texturesReady() && performance.now() - t0 < maxMs) { V.renderer.render(V.scene, V.camera); await sleep(30); }
  }
  // the fountains of the square, heard from the camera (audio.js listener)
  function fountainGain() {
    if (V.world.current) return 0;
    const p = V.camera.position; let g = 0;
    for (const fy of [60, -60]) { const d = Math.hypot(p.x, p.y - fy, p.z - 3); g = Math.max(g, clamp(26 / Math.max(d, 6), 0, 1) ** 1.3 * 0.55); }
    return g;
  }

  // ---------------------------------------------------------------- shots
  let cur = null, shotT = 0, shotSpec = null;
  F.begin = async (o = {}) => {
    F.fps = o.fps || 30;
    V.stopLoop();
    document.querySelectorAll('.ui, #fade').forEach((e) => (e.style.display = 'none'));
    await Promise.all(['city', 'core'].map((z) => V.world.load(z)));
    return true;
  };
  F.shot = async (S) => {
    shotSpec = S; cur = makeShot(S); shotT = 0;
    if (cur.zone) await V.world.load(cur.zone);
    for (const u of [0, 0.5, 1]) { cur.pose(u); V.step(0, () => cur.pose(u), true); V.renderer.render(V.scene, V.camera); await complete(); }
    for (let i = 0; i < 3; i++) { V.step(0, () => cur.pose(0), true); V.renderer.render(V.scene, V.camera); }
    return { zone: cur.zone || null };
  };
  // one frame of the current shot: step by 1/fps, draw, overlay, return a JPEG (base64)
  F.next = async (q = 0.93) => {
    const dt = 1 / F.fps, u = clamp(shotT / shotSpec.dur, 0, 1);
    V.step(dt, () => cur.pose(u), false);
    if (!texturesReady()) await complete(4000);
    V.renderer.render(V.scene, V.camera);
    F.lastInfo = { calls: V.renderer.info.render.calls, tris: V.renderer.info.render.triangles, zone: V.world.current && V.world.current.zone };
    F.camLog.push(fountainGain());
    const c = grab(); overlay(c, shotT, shotSpec);
    shotT += dt; F.frame++;
    return c.toDataURL('image/jpeg', q).split(',')[1];
  };
  F.still = async (u, q = 0.9) => {
    V.step(0, () => cur.pose(u), true); await complete(); V.renderer.render(V.scene, V.camera);
    const c = grab(); overlay(c, u * shotSpec.dur, shotSpec);
    return c.toDataURL('image/jpeg', q).split(',')[1];
  };
  // the camera of the current shot through n frames without drawing (what the sound needs to hear)
  F.trace = (n) => { for (let i = 0; i < n; i++) { const u = clamp(shotT / shotSpec.dur, 0, 1); V.step(1 / F.fps, () => cur.pose(u), false); F.camLog.push(fountainGain()); shotT += 1 / F.fps; } return F.camLog.length; };
  // the frame just drawn, read straight from the WebGL drawing buffer (drawImage of the canvas now and then got a
  // snapshot with only the sky in it); rows come bottom-up
  let C2 = null, PX = null, IMG = null;
  function grab() {
    const gl = V.renderer.getContext(), w = gl.drawingBufferWidth, h = gl.drawingBufferHeight;
    if (!C2 || C2.width !== w || C2.height !== h) { C2 = document.createElement('canvas'); C2.width = w; C2.height = h; PX = new Uint8Array(w * h * 4); IMG = C2.getContext('2d').createImageData(w, h); }
    V.renderer.setRenderTarget(null);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, PX);
    const row = w * 4;
    for (let y = 0; y < h; y++) IMG.data.set(PX.subarray((h - 1 - y) * row, (h - y) * row), y * row);
    for (let i = 3; i < IMG.data.length; i += 4) IMG.data[i] = 255;
    const g = C2.getContext('2d'); g.putImageData(IMG, 0, 0);
    return C2;
  }

  // ---------------------------------------------------------------- titles and captions (the page's own type)
  const INK = '243, 237, 226', GOLD = '#d8b766';
  const SERIF = '"Optima", "Palatino Linotype", "Palatino", "Book Antiqua", "Hiragino Mincho ProN", "Yu Mincho", "Noto Serif CJK JP", serif';
  const SANS = '"Helvetica Neue", "Hiragino Sans", "Noto Sans CJK JP", "Yu Gothic", system-ui, sans-serif';
  function fade(t, a, b, fin, fout) { return clamp(Math.min((t - a) / fin, (b - t) / fout), 0, 1); }
  function overlay(c, t, S) {
    const g = c.getContext('2d'), W = c.width, H = c.height, k = H / 1080;
    g.save(); g.textBaseline = 'alphabetic';
    if (S.title) {
      const a = fade(t, S.title.in, S.title.out, S.title.fin || 1.2, S.title.fout || 1.0);
      if (a > 0) {
        const gr = g.createLinearGradient(0, H * 0.4, 0, H); gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, `rgba(0,0,0,${0.55 * a})`);
        g.fillStyle = gr; g.fillRect(0, 0, W, H);
        const fs = Math.min(0.15 * W, 260 * k), x0 = 0.04 * W - 0.06 * fs, base = H - 0.09 * H - (S.title.sub || S.title.url ? 96 * k : 0);
        g.font = `400 ${fs}px ${SERIF}`; g.letterSpacing = `${0.14 * fs}px`;
        g.shadowColor = `rgba(0,0,0,${0.35 * a})`; g.shadowBlur = 40 * k; g.fillStyle = `rgba(255, 250, 240, ${a})`;
        g.fillText('VATICANO', x0, base); g.shadowBlur = 0;
        const line = S.title.sub || S.title.url;
        if (line) {
          g.font = `400 ${(S.title.url ? 24 : 26) * k}px ${S.title.url ? SANS : SERIF}`; g.letterSpacing = `${(S.title.url ? 0.12 : 0.06) * 26 * k}px`;
          g.fillStyle = `rgba(${INK}, ${0.88 * a})`; g.shadowColor = `rgba(0,0,0,${0.5 * a})`; g.shadowBlur = 12 * k;
          g.fillText(line, 0.04 * W + 4 * k, base + 66 * k);
        }
      }
    }
    if (S.cap) {
      const a = fade(t, 0.35, S.dur - 0.25, 0.6, 0.45);
      if (a > 0) {
        const gr = g.createLinearGradient(0, H - 300 * k, 0, H); gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, `rgba(0,0,0,${0.42 * a})`);
        g.fillStyle = gr; g.fillRect(0, H - 300 * k, W, 300 * k);
        const x = 0.04 * W, y = H - 0.09 * H;
        g.fillStyle = GOLD; g.globalAlpha = a; g.fillRect(x, y - 112 * k, 44 * k, Math.max(1, k)); g.globalAlpha = 1;
        g.shadowColor = 'rgba(0,0,0,0.45)'; g.shadowBlur = 24 * k;
        g.font = `400 ${50 * k}px ${SERIF}`; g.letterSpacing = `${0.03 * 50 * k}px`; g.fillStyle = `rgba(255, 250, 240, ${0.97 * a})`;
        g.fillText(S.cap.ja, x, y - 40 * k);
        g.shadowBlur = 10 * k; g.font = `400 ${15 * k}px ${SANS}`; g.letterSpacing = `${0.2 * 15 * k}px`; g.fillStyle = `rgba(${INK}, ${0.72 * a})`;
        g.fillText(S.cap.en.toUpperCase(), x + 2 * k, y);
      }
    }
    if (S.black) { const [t0, t1, a0, a1] = S.black, f = clamp((t - t0) / (t1 - t0), 0, 1), a = a0 + (a1 - a0) * smooth(f); if (a > 0) { g.fillStyle = `rgba(0,0,0,${a})`; g.fillRect(0, 0, W, H); } }
    g.restore();
  }

  // ---------------------------------------------------------------- sound, rendered offline
  // what: 'music' (the score from `from` for `sec` s) or 'amb' (the fountains the frames heard, and the bells)
  let wav = null;
  F.sound = async (what, o = {}) => {
    const sec = what === 'amb' ? F.camLog.length / F.fps + (o.tail || 6) : o.sec;
    const fountain = what === 'amb' ? F.camLog.slice() : null;
    const buf = await V.audio.offline(sec, o.from || 0, { fountain, bells: what === 'amb' ? o.bells || [] : [] }, what === 'music', o.until ?? Infinity);
    const n = buf.length, ch = [buf.getChannelData(0), buf.getChannelData(1)], out = new DataView(new ArrayBuffer(44 + n * 4)), rate = buf.sampleRate;
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
  F.segments = () => V.tour.segments.map((s) => ({ id: s.id, t0: s.t0, dur: s.dur, zone: s.zone, keys: s.keys.map((k) => +k[0].toFixed(2)) }));
})();
