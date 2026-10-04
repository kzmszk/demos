/* SYNTHKIT — the sounds of VENEZIA, rendered once and offline.
   The piano is the string-physics piano of ALOFT (demos/aloft) and VATICANO (demos/vatican), unchanged: stiff-string
   partials, unison strings with a slow aftersound, the hammer's felt, the soundboard's weak bass, the knock.
   Everything else is a short grain with a visible cause: a bubble, a wavelet slapping stone, a drop, an oar, a heel,
   a pigeon, a bronze bell. There are no loops and no noise beds: a grain is a few tens of milliseconds to a couple of
   seconds long, and audio.js scatters them in time.
   The function is self-contained on purpose: audio.js sends synthKit.toString() to a Blob worker. */
export function synthKit() {
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  let seed = 1;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const gauss = () => { let s = 0; for (let i = 0; i < 4; i++) s += rnd(); return (s - 2) * 1.7; };

  /* one struck note: stiff-string partials (each a pair of slightly detuned strings decaying fast, plus
     a slow aftersound), the hammer's comb and felt, the soundboard's weak bass radiation, and the knock */
  function note(m, need = 99) {
    seed = 1000 + m * 7;
    const rate = m < 50 ? 22050 : 32000;
    const f0 = 440 * Math.pow(2, (m - 69) / 12);
    const B = m >= 48 ? Math.pow(10, -3.7 + 0.035 * (m - 48)) : Math.pow(10, -3.7 + 0.011 * (48 - m));
    const dur = Math.max(1.2, Math.min(clamp(11 - (m - 24) * 0.115, 2.6, 11), need + 0.6));
    const N = Math.floor(dur * rate), acc = new Float64Array(N);
    const b1 = 0.2 + 0.35 * Math.pow(2, (m - 60) / 12), b3 = 3e-7;
    const fmax = Math.min(rate * 0.45, 12000);
    const beta = 0.122;                                   /* the hammer strikes an eighth of the way along */
    const fc = 900 * Math.pow(2, (m - 60) / 24);          /* felt corner: harder and higher in the treble */
    const strings = m < 34 ? 1 : m < 46 ? 2 : 3;
    for (let n = 1; ; n++) {
      const fn = n * f0 * Math.sqrt(1 + B * n * n);
      if (fn > fmax) break;
      let a = Math.abs(Math.sin(Math.PI * n * beta)) + 0.05;
      a *= 1 / (1 + (fn / fc) * (fn / fc));
      a *= (fn * fn) / (fn * fn + 110 * 110);              /* the soundboard barely radiates the lowest fundamentals */
      if (a < 1e-5) continue;
      const aft = b1 + b3 * fn * fn, prompt = aft * 2.6 + 0.3;
      const comps = [[0.6, prompt, 0]];
      if (strings > 1) comps.push([0.32, prompt * 1.12, 0.00019 * (1 + 0.3 * gauss())]);
      if (strings > 2) comps.push([0.22, prompt * 0.9, -0.00014 * (1 + 0.3 * gauss())]);
      comps.push([0.16, aft, 0.00008 * gauss()]);
      for (const [k, alpha, det] of comps) {
        const amp = a * k, w = (2 * Math.PI * fn * (1 + det)) / rate, r = Math.exp(-alpha / rate);
        const life = Math.min(N, Math.ceil((Math.log(amp / 2e-6) / alpha) * rate));
        if (life < 4) continue;
        const c1 = 2 * r * Math.cos(w), c2 = r * r;
        let y1 = 0, y0 = amp * r * Math.sin(w);
        acc[1] += y0;
        for (let i = 2; i < life; i++) { const y = c1 * y0 - c2 * y1; y1 = y0; y0 = y; acc[i] += y; }
      }
    }
    /* the knock: the hammer and key against the frame, ringing a few soundboard modes */
    const knock = 0.05 + 0.25 * clamp((m - 40) / 60, 0, 1);
    for (const [fk, tk] of [[96, 0.05], [143, 0.04], [212, 0.03], [287, 0.025], [415, 0.018], [620, 0.012]]) {
      const w = (2 * Math.PI * fk * (1 + 0.04 * gauss())) / rate, r = Math.exp(-1 / (tk * rate)), c1 = 2 * r * Math.cos(w), c2 = r * r;
      let y1 = 0, y0 = knock * 0.012 * (0.6 + 0.8 * rnd()) * r * Math.sin(w);
      const life = Math.min(N, Math.ceil(tk * 9 * rate));
      for (let i = 1; i < life; i++) { const y = c1 * y0 - c2 * y1; y1 = y0; y0 = y; acc[i] += y; }
    }
    /* level: equal loudness across the keyboard, measured over the first moments */
    let e = 0; const win = Math.floor(0.35 * rate);
    for (let i = 0; i < win; i++) e += acc[i] * acc[i];
    const rms = Math.sqrt(e / win) || 1, tilt = m < 60 ? 1 + (60 - m) * 0.004 : 1 - (m - 60) * 0.006;
    const g = (0.2 * tilt) / rms, out = new Float32Array(N), fin = Math.floor(0.0006 * rate), fout = Math.floor(0.25 * rate);
    for (let i = 0; i < N; i++) {
      let s = acc[i] * g;
      if (i < fin) s *= i / fin;
      if (i > N - fout) s *= 0.5 + 0.5 * Math.cos((Math.PI * (i - (N - fout))) / fout);
      out[i] = s;
    }
    return { m, rate, data: [out] };
  }

  /* ====================================================================================================
     the natural sounds
     ==================================================================================================== */
  const TAU = Math.PI * 2;
  let R = 32000;                                          /* the working rate of the grain being made */
  function biquad(type, f, q, rate) {
    const w = (TAU * f) / rate, cs = Math.cos(w), al = Math.sin(w) / (2 * q), a0 = 1 + al;
    let b0, b1, b2;
    if (type === 'bp') { b0 = al; b1 = 0; b2 = -al; }
    else if (type === 'hp') { b0 = (1 + cs) / 2; b1 = -(1 + cs); b2 = (1 + cs) / 2; }
    else { b0 = (1 - cs) / 2; b1 = 1 - cs; b2 = (1 - cs) / 2; }
    const B0 = b0 / a0, B1 = b1 / a0, B2 = b2 / a0, A1 = (-2 * cs) / a0, A2 = (1 - al) / a0;
    let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    return (x) => { const y = B0 * x + B1 * x1 + B2 * x2 - A1 * y1 - A2 * y2; x2 = x1; x1 = x; y2 = y1; y1 = y; return y; };
  }
  /* a gas bubble's ring (Minnaert): a decaying sine whose pitch climbs as the bubble nears the surface.
     A bubble of radius r rings at about 3.26 / r hertz; its damping follows its pitch. */
  const damp = (f) => 0.043 * f + 0.0014 * Math.pow(f, 1.5);
  function ring(b, at, f, amp, o = {}) {
    at = Math.floor(at); if (at < 0 || at >= b.length) return;
    const d = o.d || damp(f), xi = o.xi ?? 0.1 + 0.4 * rnd();
    const n = Math.min(Math.ceil((o.len || 7 / d) * R), b.length - at);
    let ph = o.ph || 0;
    for (let i = 0; i < n; i++) {
      const t = i / R;
      ph += (TAU * f * (1 + xi * d * t)) / R;
      b[at + i] += amp * Math.sin(ph) * Math.exp(-d * t) * Math.min(1, i / 6);
    }
  }
  /* a short burst of band-limited noise: the skin of a splash, the click of a heel */
  function burst(b, at, f, q, tau, amp, atk = 0.0006) {
    at = Math.floor(at); if (at < 0 || at >= b.length) return;
    const bp = biquad('bp', f, q, R), n = Math.min(Math.ceil(tau * 7 * R), b.length - at), a = Math.max(2, Math.floor(atk * R));
    for (let i = 0; i < n; i++) b[at + i] += bp(rnd() * 2 - 1) * amp * Math.min(1, i / a) * Math.exp(-i / (tau * R));
  }
  /* a cloud of small bubbles, thickest at the start: what the froth does when it falls back */
  function cloud(b, at, count, span, fLo, fHi, amp, skew = 1.2, front = 3) {
    for (let k = 0; k < count; k++) {
      const t = (span * -Math.log(1 - rnd() * (1 - Math.exp(-front)))) / front;
      const f = fLo * Math.pow(fHi / fLo, Math.pow(rnd(), skew));
      ring(b, at + t * R, f, amp * (0.25 + rnd()) * Math.pow(f / 1200, -0.5));
    }
  }
  /* a damped, unglided resonance: a heel on a slab, a wing's thump */
  const tock = (b, at, f, amp, tau) => ring(b, at, f, amp, { d: 1 / tau, xi: 0, len: tau * 7 });
  /* high-pass (and low-pass), fade the ends, normalise the peak */
  function finish(b, o = {}) {
    const n = b.length, out = new Float32Array(n), hp = o.hp || 180, lp = o.lp || 0;
    const h1 = biquad('hp', hp, 0.7, R), h2 = biquad('hp', hp, 0.7, R), l1 = lp ? biquad('lp', lp, 0.7, R) : null;
    let pk = 1e-9;
    for (let i = 0; i < n; i++) { let x = h2(h1(b[i])); if (l1) x = l1(x); if (!Number.isFinite(x)) x = 0; out[i] = x; if (Math.abs(x) > pk) pk = Math.abs(x); }
    const g = (o.peak ?? 0.9) / pk, fin = Math.floor((o.fin ?? 0.0004) * R), fout = Math.min(n >> 1, Math.floor((o.fout ?? 0.02) * R));
    for (let i = 0; i < n; i++) {
      let s = out[i] * g;
      if (i < fin) s *= i / fin;
      if (i > n - fout) s *= 0.5 + 0.5 * Math.cos((Math.PI * (i - (n - fout))) / fout);
      out[i] = s;
    }
    return { rate: R, data: [out] };
  }
  const log = (lo, hi) => lo * Math.pow(hi / lo, rnd());

  /* ---- water ---- */
  /* a drop falling on water: the tick of the impact and the little bubble it traps, sometimes a second plip */
  function drip() {
    R = 32000; const b = new Float64Array(Math.floor(0.4 * R));
    const f = log(1000, 3200);
    burst(b, 4, 3600, 1.2, 0.0010, 0.3);
    ring(b, 5, f, 1, { xi: 0.1 + 0.2 * rnd(), d: damp(f) * 0.7 });
    if (rnd() < 0.5) ring(b, (0.04 + 0.07 * rnd()) * R, f * (0.6 + 0.3 * rnd()), 0.25 + 0.25 * rnd(), { xi: 0.08 + 0.15 * rnd(), d: damp(f) * 0.8 });
    return finish(b, { hp: 500, peak: 0.8 });
  }
  /* a larger bubble coming up: blup */
  function bubble() {
    R = 32000; const b = new Float64Array(Math.floor(0.45 * R));
    const f = log(300, 950);
    ring(b, 6, f, 1, { xi: 0.18 + 0.3 * rnd(), d: damp(f) * 0.85 });
    if (rnd() < 0.4) ring(b, (0.05 + 0.08 * rnd()) * R, f * (1.2 + 0.5 * rnd()), 0.35, { xi: 0.2 });
    return finish(b, { hp: 200, peak: 0.85 });
  }
  /* a wavelet slapping a stone wall: a hollow clop from the air in the stone, the wet slap, froth falling back */
  function slap() {
    R = 32000; const b = new Float64Array(Math.floor(0.55 * R));
    const fc = log(260, 640);
    ring(b, 10, fc, 0.7, { d: damp(fc) * 0.9, xi: 0.05 + 0.1 * rnd() });
    burst(b, 5, log(1500, 3200), 0.9, 0.010 + 0.012 * rnd(), 0.65);
    cloud(b, 18, 10 + Math.floor(14 * rnd()), 0.2, 900, 5200, 0.25);
    if (rnd() < 0.5) ring(b, (0.07 + 0.08 * rnd()) * R, fc * (0.75 + 0.3 * rnd()), 0.25, { d: damp(fc), xi: 0.08 });
    return finish(b, { hp: 190, lp: 8500, peak: 0.85 });
  }
  /* water running up a stone step and draining back: a swell of froth, a few glugs, a trickle */
  function lap() {
    R = 32000; const T = 0.75 + 0.3 * rnd(), b = new Float64Array(Math.floor(T * R)), rise = 0.08 + 0.08 * rnd(), tau = 0.15 + 0.12 * rnd();
    const dens = (t) => (t < rise ? 0.25 + 0.75 * Math.sin((Math.PI * t) / (2 * rise)) : Math.exp(-(t - rise) / tau));
    const L = 760 * T;
    for (let k = 0; k < L; k++) {
      const t = rnd() * T; if (rnd() > dens(t)) continue;
      const f = log(1100, 6200);
      ring(b, t * R, f, 0.075 * (0.3 + rnd()) * Math.pow(f / 1500, -0.4));
    }
    burst(b, 8, log(1400, 2400), 0.8, 0.030 + 0.03 * rnd(), 0.35);
    for (let k = 0, c = 2 + Math.floor(rnd() * 4); k < c; k++) { const f = log(330, 760); ring(b, (rise * 0.6 + 0.6 * rnd() * T) * R, f, 0.2 + 0.2 * rnd(), { xi: 0.12 + 0.25 * rnd(), d: damp(f) * 0.85 }); }
    return finish(b, { hp: 200, lp: 8500, peak: 0.8, fout: 0.08 });
  }
  /* a splash: skin, spray, a few big bubbles under it */
  function splash() {
    R = 32000; const b = new Float64Array(Math.floor(0.75 * R));
    burst(b, 5, 1500, 0.7, 0.05, 0.7); burst(b, 5, log(3600, 4800), 0.9, 0.02, 0.45);
    cloud(b, 10, 32 + Math.floor(30 * rnd()), 0.36, 700, 5200, 0.2, 1.1, 2.5);
    for (let k = 0; k < 3; k++) { const f = log(380, 900); ring(b, (0.02 + 0.25 * rnd()) * R, f, 0.3 + 0.2 * rnd(), { xi: 0.25 }); }
    return finish(b, { hp: 200, lp: 8500, peak: 0.85, fout: 0.06 });
  }
  /* a wavelet against a wooden hull: a soft swell, a small woody clop, a few bubbles, nothing sharp */
  function hull() {
    R = 32000; const b = new Float64Array(Math.floor(0.6 * R)), bp = biquad('bp', log(700, 1300), 0.7, R);
    const n = Math.floor(0.4 * R), top = (0.014 + 0.02 * rnd()) * R, amp = 0.5;
    for (let i = 0; i < n; i++) b[i + 6] += bp(rnd() * 2 - 1) * amp * Math.min(1, i / top) * Math.exp(-i / (0.08 * R));
    const f = log(360, 560);
    ring(b, (0.01 + 0.02 * rnd()) * R, f, 0.35, { d: damp(f) * 0.8, xi: 0.08 });
    cloud(b, 0.015 * R, 12 + Math.floor(12 * rnd()), 0.3, 700, 3600, 0.2, 1.3, 3);
    return finish(b, { hp: 200, lp: 3800, peak: 0.7, fout: 0.05 });
  }
  /* the oar: the blade goes in (a splash), the vortices behind it speak as it pulls (a few bloops), and it slips out */
  function oar() {
    R = 32000; const b = new Float64Array(Math.floor(1.25 * R));
    burst(b, 4, 1700, 0.7, 0.04, 0.8, 0.003); burst(b, 4, 4000, 0.9, 0.014, 0.4, 0.002);
    cloud(b, 4, 24 + Math.floor(10 * rnd()), 0.16, 800, 5000, 0.2, 1.1, 3);
    const k = 3 + Math.floor(rnd() * 3);
    for (let i = 0; i < k; i++) { const f = log(290, 700) * (1 - 0.04 * i); ring(b, (0.07 + 0.17 * i + 0.05 * rnd()) * R, f, 0.42 * Math.pow(0.78, i), { xi: 0.18 + 0.3 * rnd(), d: damp(f) * 0.8 }); }
    cloud(b, 0.03 * R, 120, 0.7, 900, 4200, 0.09, 1.2, 1.2);
    const out = (0.78 + 0.08 * rnd()) * R;
    burst(b, out, 2200, 1, 0.006, 0.2); cloud(b, out, 8, 0.1, 1200, 4200, 0.1);
    return finish(b, { hp: 190, lp: 7000, peak: 0.85, fout: 0.1 });
  }

  /* ---- a person on stone ---- */
  /* a leather heel on a flagstone: a soft click, the slab's short hollow tock, a little scuff; walking adds the forefoot */
  function step(run) {
    R = 32000; const b = new Float64Array(Math.floor(0.3 * R));
    const f = log(180, 250) * (run ? 1.12 : 1), a = run ? 1.1 : 1;
    burst(b, 2, log(2300, 3300), 1.3, 0.0018, 0.3 * a, 0.0003);
    tock(b, 3, f, 1 * a, 0.02); tock(b, 3, f * 2.3, 0.5 * a, 0.012); tock(b, 3, f * 4.1 * (0.9 + 0.2 * rnd()), 0.22 * a, 0.007);
    burst(b, 4, log(1800, 2800), 0.8, 0.02, run ? 0.15 : 0.07, 0.004);
    if (!run) { const t = (0.085 + 0.03 * rnd()) * R; tock(b, t, f * 1.3, 0.38, 0.016); burst(b, t, 2600, 1.2, 0.0016, 0.14, 0.0003); }
    return finish(b, { hp: 150, lp: 6500, peak: 0.8, fout: 0.04 });
  }

  /* ---- a pigeon ---- */
  /* a coo: "oo – ROO – coo" — a harmonic tone with a vowel's formant, a rising swell, a rolled middle (a fast tremolo)
     and a falling, wavering end; one or two phrases */
  function coo() {
    R = 22050; const T = 1.7, b = new Float64Array(Math.floor(T * R)), base = 380 * (0.9 + 0.3 * rnd());
    let ph = 0;
    const phrases = rnd() < 0.55 ? 1 : 2;
    for (let p = 0; p < phrases; p++) {
      const t0 = 0.04 + p * (0.78 + 0.1 * rnd()), pitch = 1 + 0.06 * gauss() * 0.4, g = 1 - 0.18 * p;
      for (const [s, d, f0, f1, roll, vib] of [[0, 0.14, 0.9, 1.05, 0, 0], [0.17, 0.3, 1.1, 1.28, 0.55, 0], [0.5, 0.55, 1.22, 0.82, 0.12, 0.014]]) {
        const i0 = Math.floor((t0 + s) * R), n = Math.floor(d * R);
        for (let i = 0; i < n && i0 + i < b.length; i++) {
          const t = i / R, u = i / n;
          const f = base * pitch * (f0 + (f1 - f0) * Math.pow(u, 0.8)) * (1 + vib * Math.sin(TAU * 6.5 * t));
          ph += (TAU * f) / R;
          let y = 0;
          for (let h = 1; h <= 7; h++) { const fh = f * h; if (fh > 4200) break; y += Math.sin(h * ph) * (1 / Math.pow(h, 1.5)) * (1 / (1 + Math.pow((fh - 950) / 800, 2))); }
          const env = Math.pow(Math.sin(Math.PI * Math.min(1, u * 0.92 + 0.04)), 1.1) * (s > 0.4 ? 1 - 0.35 * u : 1);
          const am = 1 - roll + roll * (0.5 + 0.5 * Math.sin(TAU * 26 * t));
          b[i0 + i] += y * env * am * g;
        }
      }
    }
    const bp = biquad('bp', 1100, 0.8, R);
    for (let i = 0; i < b.length; i++) b[i] += bp(rnd() * 2 - 1) * 0.03 * Math.min(1, Math.abs(b[i]) * 8);
    return finish(b, { hp: 200, lp: 4500, peak: 0.8, fout: 0.05 });
  }
  /* pigeons taking off: a few birds' wing claps, quick at first and slowing, rising and fading as they go */
  function wing() {
    R = 32000; const T = 1.5 + 0.5 * rnd(), b = new Float64Array(Math.floor(T * R)), birds = 2 + Math.floor(rnd() * 3);
    for (let k = 0; k < birds; k++) {
      let t = 0.02 + 0.3 * rnd(), iv = 0.075 + 0.02 * rnd(); const claps = 7 + Math.floor(rnd() * 8), pan = 0.6 + 0.4 * rnd();
      for (let c = 0; c < claps && t < T - 0.1; c++) {
        const env = Math.min(1, 0.35 + c * 0.2) * Math.pow(1 - c / (claps + 2), 0.8) * pan;
        burst(b, t * R, log(1500, 3200), 0.9, 0.006 + 0.004 * rnd(), 0.5 * env, 0.0008);
        tock(b, t * R, log(330, 520), 0.22 * env, 0.011);
        t += iv * (0.9 + 0.2 * rnd()); iv *= 1.045;
      }
    }
    return finish(b, { hp: 220, lp: 6000, peak: 0.8, fout: 0.2 });
  }

  /* ---- a bronze bell ---- */
  /* the classic partials of a church bell: hum, prime, tierce (a minor third), quint, nominal, and a handful of higher
     modes, each one a pair of slightly detuned oscillations so that it beats as it dies; three sizes (id 0 big .. 2 small);
     audio.js transposes them to the pitch it wants */
  const BELL = [[0.5, 0.5, 9], [1.0, 0.65, 6], [1.183, 0.42, 4.5], [1.506, 0.2, 3.5], [2.0, 0.5, 3.2], [2.514, 0.16, 2.2], [2.662, 0.12, 2], [3.011, 0.12, 1.8], [4.166, 0.08, 1.2], [5.433, 0.05, 0.8]];
  function bell(id) {
    R = 22050;
    const [prime, scale, dur] = [[196, 1.55, 24], [330, 1.0, 15], [523, 0.62, 9]][id];
    const N = Math.floor(dur * R), b = new Float64Array(N);
    for (const [r, a, t] of BELL) {
      const f = prime * r * (1 + 0.0015 * gauss()), d = 1 / (t * scale), beat = (0.25 + 1.0 * rnd()) * (0.6 + 0.3 * r);
      for (const [df, k] of [[0, 1], [beat, 0.62]]) {
        const w = (TAU * (f + df)) / R, ph = rnd() * TAU, g = a * k, life = Math.min(N, Math.ceil((Math.log(g / 1e-4) / d) * R));
        for (let i = 0; i < life; i++) b[i] += g * Math.sin(w * i + ph) * Math.exp((-d * i) / R);
      }
    }
    /* the strike: the clapper's knock and the quickly dying high modes */
    burst(b, 0, 2400, 0.8, 0.005, 0.28, 0.0008);
    for (const [r, a, t] of [[6.9, 0.07, 0.18], [9.3, 0.045, 0.12], [12.1, 0.03, 0.08]]) ring(b, 0, prime * r * (1 + 0.003 * gauss()), a, { d: 1 / t, xi: 0, len: t * 6 });
    return finish(b, { hp: 60, peak: 0.8, fin: 0.004, fout: 0.6 });
  }

  /* how many variants of each grain, and how to make them */
  const MAKERS = { drip, bubble, slap, lap, splash, hull, oar, walk: () => step(false), run: () => step(true), coo, wing, bell: null };
  const COUNTS = { drip: 12, bubble: 8, slap: 10, lap: 10, splash: 5, hull: 8, oar: 5, walk: 8, run: 5, coo: 6, wing: 5, bell: 3 };
  const KINDS = Object.keys(COUNTS);
  function sfx(kind, id) {
    seed = 1013 + KINDS.indexOf(kind) * 7919 + id * 104729;
    for (let i = 0; i < 5; i++) rnd();
    const g = kind === 'bell' ? bell(id) : MAKERS[kind]();
    return { kind, id, rate: g.rate, data: g.data };
  }
  return { note, sfx, COUNTS };
}
