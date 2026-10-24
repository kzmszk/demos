// film_page.js — evaluated in the TOKYO 2090 page by film.mjs: the game stepped at a fixed rate with the glider put
// where each shot wants it (T2090.film.frame with a pose), every frame read straight from the WebGL buffer, the
// captions, Saki's lines and the titles drawn over it in the game's own type, and the sound rendered offline by the
// game's own engine (the Gymnopédie, the higurashi and the birds).
(() => {
  const T = window.T2090, FM = T.film, THREE = FM.THREE;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const smooth = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
  const ease = (e) => (e === 'inout' ? smooth : e === 'out' ? (u) => 1 - (1 - clamp(u, 0, 1)) ** 2 : e === 'in' ? (u) => clamp(u, 0, 1) ** 2 : (u) => clamp(u, 0, 1));
  const F = window.FILM = { fps: 30, frame: 0 };

  // ---------------------------------------------------------------- the shots: where the glider (and so the eyes) is at
  // shot time t (seconds; negative while it runs in)
  function makeShot(S) {
    const E = ease(S.ease), W = T.walker;
    const stand = (f, x, y, h) => { const z = W.under(x, y); f.p.set(x, z + 1.65, -y); f.feet = z; f.eye = z + 1.65; f.setHeading(h); f.walkHeading = h; };
    const fly = (f, x, y, z, h, speed, roll, up) => {
      f.state = 'glide'; f.open = 1; f.hand = false; f.close = false; f.launch = null; f.target = null; f.dropping = false;
      f.p.set(x, z, -y); f.setHeading(h); f.roll = roll; f.gamma = -0.07; f.speed = speed; f.updraft = up; f.stateTime = 10;
      f.v.set(Math.sin(h) * speed, -0.07 * speed, -Math.cos(h) * speed);
    };
    if (S.kind === 'pan') return {
      start(f) { f.placeOnFoot(S.x, S.y, S.h); },
      pose(f, look, t) { const u = t / S.dur; look.yaw = S.sweep * E(u); look.pitch = S.p; },
    };
    if (S.kind === 'ground') return {
      start(f) { f.placeOnFoot(S.a[0], S.a[1], S.h0); },
      pose(f, look, t) {
        const u = E(t / S.dur), x = S.a[0] + (S.b[0] - S.a[0]) * u, y = S.a[1] + (S.b[1] - S.a[1]) * u;
        stand(f, x, y, S.h0 + (S.h1 - S.h0) * u); look.yaw = 0; look.pitch = S.p0 + (S.p1 - S.p0) * u;
      },
    };
    if (S.kind === 'arc') return {
      // on foot (or crouched: eye `eye` m above the ground), arcing around the point c at radius r0 -> r1 from angle
      // a0 to a1 (radians from east, counter-clockwise), always facing it, the eyes on the height zl above c's ground
      start(f) { f.placeOnFoot(S.c[0] + S.r0 * Math.cos(S.a0), S.c[1] + S.r0 * Math.sin(S.a0), 0); },
      pose(f, look, t) {
        const u = E(t / S.dur), a = S.a0 + (S.a1 - S.a0) * u, r = S.r0 + (S.r1 - S.r0) * u;
        const x = S.c[0] + r * Math.cos(a), y = S.c[1] + r * Math.sin(a), h = Math.atan2(S.c[0] - x, S.c[1] - y);
        stand(f, x, y, h); f.p.y += (S.eye ?? 1.65) - 1.65;
        const zc = W.under(S.c[0], S.c[1]) + S.zl; look.yaw = 0; look.pitch = Math.atan2(zc - f.p.y, r) + (S.tilt || 0);
      },
    };
    if (S.kind === 'glide') return {
      start(f) {},
      pose(f, look, t) {
        const fx = Math.sin(S.h), fy = Math.cos(S.h), d = S.speed * t;
        fly(f, S.x + fx * d, S.y + fy * d, S.z + S.climb * t, S.h + S.sway * 0.25 * Math.sin(t * 0.33), S.speed, S.sway * Math.sin(t * 0.5), S.climb);
        look.yaw = S.look[0] / 0.4; look.pitch = S.look[1] / 0.5;
      },
    };
    if (S.kind === 'orbit') return {
      start(f) {},
      pose(f, look, t) {
        const a = S.a0 + S.speed / S.r * t, x = S.c[0] + S.r * Math.cos(a), y = S.c[1] + S.r * Math.sin(a);
        const z = S.z0 + (S.z1 - S.z0) * t / S.dur;
        fly(f, x, y, z, Math.atan2(-Math.sin(a), Math.cos(a)), S.speed, -S.bank, (S.z1 - S.z0) / S.dur);
        look.yaw = S.inward / 0.4; look.pitch = S.pitch / 0.5;
      },
    };
    throw new Error('shot kind ' + S.kind);
  }

  // ---------------------------------------------------------------- everything in view is loaded
  function settled() {
    const C = T.city, cam = T.camera.position;
    if (!C || C.loading > 0) return false;
    for (const t of C.tiles.values()) {
      if (t.state === 0 || t.state === 1) return false;
      if (t.state === 2) { const c = C.tileCenter(t.head); if (Math.hypot(c.x - cam.x, c.z - cam.z) < C.fullRadius && t.mesh.geometry !== t.full) return false; }
    }
    for (const d of FM.heroes.districts) if (Object.values(d.loading).some(Boolean)) return false;
    return !!T.props;
  }
  async function complete(pose, maxMs = 60000) {
    const t0 = performance.now();
    do { FM.frame(0, pose, true); await sleep(40); } while (!settled() && performance.now() - t0 < maxMs);
    for (let i = 0; i < 4; i++) { FM.frame(0, pose, true); await sleep(30); }
  }

  // ---------------------------------------------------------------- shots
  let cur = null, spec = null, shotT = 0;
  const poseAt = (t) => (f, look) => cur.pose(f, look, t);
  F.begin = async (o = {}) => {
    F.fps = o.fps || 30;
    FM.stop(); T.renderer.setPixelRatio(1);
    document.querySelectorAll('.hud, .hint, #say, #places, #placesBtn, #mute, #intro, #loading, #fade, #lift, .tbtn, #stick').forEach((e) => (e.style.display = 'none'));
    FM.labels.enabled = false;
    // the whole city in (every tile; the far ones are cheap)
    await complete((f, look) => {}, 120000);
    return { tiles: T.city.ready };
  };
  F.shot = async (S) => {
    spec = S; cur = makeShot(S); shotT = 0; FM.thermals = !!S.thermals; FM.lift = S.lift || 0;      // the rising seeds only where the shot is about the lift
    const f = T.flight; cur.start(f);
    for (const t of [S.dur, S.dur * 0.5, 0]) await complete(poseAt(t));
    // run in: a second and a half before the shot, so Saki and the eyes' easing are already moving with it
    if (S.kind === 'glide' || S.kind === 'orbit') {
      const f2 = T.flight; cur.pose(f2, FM.look, -1.5);
      FM.saki.place(f2.p.clone().addScaledVector(f2.forward, 7.5).addScaledVector(f2.right, 3.2));
    }
    for (let i = -45; i < 0; i++) FM.frame(1 / F.fps, poseAt(i / F.fps), i === -45);
    return { settled: settled() };
  };
  F.next = async (q = 0.92) => {
    const dt = 1 / F.fps;
    FM.frame(dt, poseAt(shotT), false);
    if (!settled()) { await complete(poseAt(shotT), 8000); FM.frame(0, poseAt(shotT), false); }
    const c = grab(); overlay(c, shotT, spec);
    shotT += dt; F.frame++;
    return c.toDataURL('image/jpeg', q).split(',')[1];
  };
  F.still = async (u, q = 0.9) => {
    const t = u * spec.dur;
    await complete(poseAt(t), 20000);
    for (let i = 0; i < 30; i++) FM.frame(1 / F.fps, poseAt(t - (30 - i) / F.fps), false);
    FM.frame(1 / F.fps, poseAt(t), false);
    const c = grab(); overlay(c, t, spec);
    return c.toDataURL('image/jpeg', q).split(',')[1];
  };
  // the frame just drawn, read from the drawing buffer (rows come bottom-up)
  let C2 = null, PX = null, IMG = null;
  function grab() {
    const gl = T.renderer.getContext(), w = gl.drawingBufferWidth, h = gl.drawingBufferHeight;
    if (!C2 || C2.width !== w || C2.height !== h) { C2 = document.createElement('canvas'); C2.width = w; C2.height = h; PX = new Uint8Array(w * h * 4); IMG = C2.getContext('2d').createImageData(w, h); }
    T.renderer.setRenderTarget(null);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, PX);
    const row = w * 4;
    for (let y = 0; y < h; y++) IMG.data.set(PX.subarray((h - 1 - y) * row, (h - y) * row), y * row);
    for (let i = 3; i < IMG.data.length; i += 4) IMG.data[i] = 255;
    C2.getContext('2d').putImageData(IMG, 0, 0);
    return C2;
  }

  // ---------------------------------------------------------------- titles, places, Saki's lines (the game's type)
  const SANS = '-apple-system, "Helvetica Neue", Helvetica, "Hiragino Sans", "Noto Sans CJK JP", "Noto Sans JP", sans-serif';
  const FG = '242, 236, 226', CAPE = '#c4533a';
  const fade = (t, a, b, fin, fout) => clamp(Math.min((t - a) / fin, (b - t) / fout), 0, 1);
  function overlay(c, t, S) {
    const g = c.getContext('2d'), W = c.width, H = c.height, k = H / 1080, x0 = 0.045 * W;
    g.save(); g.textBaseline = 'alphabetic';
    if (S.title) {
      const a = fade(t, S.title.in, S.title.out, S.title.fin || 1.2, S.title.fout || 1.0);
      if (a > 0) {
        const gr = g.createLinearGradient(0, H * 0.35, 0, H); gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, `rgba(8,6,5,${0.6 * a})`);
        g.fillStyle = gr; g.fillRect(0, 0, W, H);
        const fs = 196 * k, base = H - 0.1 * H - 70 * k;
        g.font = `800 ${fs}px ${SANS}`; g.letterSpacing = `${-0.045 * fs}px`;
        g.shadowColor = `rgba(0,0,0,${0.4 * a})`; g.shadowBlur = 40 * k; g.fillStyle = `rgba(${FG}, ${a})`;
        g.fillText('TOKYO 2090', x0 - 0.04 * fs, base); g.shadowBlur = 0;
        const line = S.title.sub || S.title.url;
        g.font = `400 ${(S.title.url ? 22 : 20) * k}px ${SANS}`; g.letterSpacing = `${(S.title.url ? 0.16 : 0.34) * 20 * k}px`;
        g.fillStyle = `rgba(${FG}, ${0.8 * a})`; g.shadowColor = `rgba(0,0,0,${0.5 * a})`; g.shadowBlur = 10 * k;
        g.fillText(line, x0 + 4 * k, base + 70 * k);
      }
    }
    if (S.cap) {
      const a = fade(t, S.cap.in, S.cap.out, 0.6, 0.5);
      if (a > 0) {
        const gr = g.createLinearGradient(0, H - 280 * k, 0, H); gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, `rgba(8,6,5,${0.45 * a})`);
        g.fillStyle = gr; g.fillRect(0, H - 280 * k, W, 280 * k);
        const y = H - 0.085 * H;
        g.globalAlpha = a; g.fillStyle = CAPE; g.fillRect(x0, y - 98 * k, 36 * k, 3 * k); g.globalAlpha = 1;
        g.shadowColor = 'rgba(0,0,0,0.5)'; g.shadowBlur = 18 * k;
        g.font = `700 ${44 * k}px ${SANS}`; g.letterSpacing = `${0.06 * 44 * k}px`; g.fillStyle = `rgba(${FG}, ${0.97 * a})`;
        g.fillText(S.cap.ja, x0, y - 34 * k);
        g.shadowBlur = 8 * k; g.font = `400 ${15 * k}px ${SANS}`; g.letterSpacing = `${0.26 * 15 * k}px`; g.fillStyle = `rgba(${FG}, ${0.7 * a})`;
        g.fillText(S.cap.en.toUpperCase(), x0 + 2 * k, y);
      }
    }
    if (S.say) {
      const a = fade(t, S.say.in, S.say.out, 0.9, 0.9);
      if (a > 0) {
        const fs = 30 * k; g.font = `400 ${fs}px ${SANS}`; g.letterSpacing = `${0.12 * fs}px`;
        const w = g.measureText(S.say.text).width, cx = W / 2, cy = H * 0.27, px = 34 * k, ph = 20 * k;
        g.fillStyle = `rgba(14,10,8,${0.42 * a})`; g.fillRect(cx - w / 2 - px, cy - fs - ph * 0.6, w + 2 * px, fs + ph * 1.6);
        g.textAlign = 'center'; g.shadowColor = `rgba(0,0,0,${0.85 * a})`; g.shadowBlur = 12 * k; g.fillStyle = `rgba(246, 217, 203, ${a})`;
        g.fillText(S.say.text, cx + 0.06 * fs, cy); g.textAlign = 'left'; g.shadowBlur = 0;
      }
    }
    if (S.black) { const [t0, t1, a0, a1] = S.black, a = a0 + (a1 - a0) * smooth((t - t0) / (t1 - t0)); if (a > 0) { g.fillStyle = `rgba(0,0,0,${a})`; g.fillRect(0, 0, W, H); } }
    if (S.fadeIn) { const a = 1 - smooth(t / S.fadeIn); if (a > 0) { g.fillStyle = `rgba(0,0,0,${a})`; g.fillRect(0, 0, W, H); } }
    g.restore();
  }

  // ---------------------------------------------------------------- sound, rendered offline by the game's engine
  let wav = null;
  F.sound = async (what, sec) => {
    const R = 48000, oac = new OfflineAudioContext(2, Math.ceil(sec * R), R);
    const layers = what === 'music' ? { music: true, cicada: false, birds: false, breath: false } : { music: false, cicada: true, birds: true, breath: false };
    const a = FM.createAudio({ context: oac, manual: true, layers });
    // schedule as the game does, a couple of seconds ahead of the render: scheduling the whole film at once ran the
    // engine's voice cap, which killed every early note before it sounded (only the last ~18 s had music)
    a.start(); a.setFlying(false); a._pump(2);
    for (let t = 1; t < sec; t += 1) oac.suspend(t).then(() => { a._pump(t + 2); oac.resume(); });
    const buf = await oac.startRendering();
    const n = buf.length, ch = [buf.getChannelData(0), buf.getChannelData(1)], out = new DataView(new ArrayBuffer(44 + n * 4));
    const str = (o, s) => { for (let i = 0; i < s.length; i++) out.setUint8(o + i, s.charCodeAt(i)); };
    str(0, 'RIFF'); out.setUint32(4, 36 + n * 4, true); str(8, 'WAVEfmt '); out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, 2, true);
    out.setUint32(24, R, true); out.setUint32(28, R * 4, true); out.setUint16(32, 4, true); out.setUint16(34, 16, true); str(36, 'data'); out.setUint32(40, n * 4, true);
    for (let i = 0, p = 44; i < n; i++) for (let c = 0; c < 2; c++, p += 2) out.setInt16(p, clamp(Math.round(ch[c][i] * 32767), -32768, 32767), true);
    const bytes = new Uint8Array(out.buffer); let b64 = '';
    for (let i = 0; i < bytes.length; i += 0x8000) b64 += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    wav = btoa(b64);
    return Math.ceil(wav.length / 4e6);
  };
  F.chunk = (i) => wav.slice(i * 4e6, (i + 1) * 4e6);
})();
