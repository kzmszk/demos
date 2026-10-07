/* SYNTHKIT — the sounds of KYOTO, rendered once and offline.
   The piano is the string-physics piano of ALOFT, VATICANO and VENEZIA, unchanged: stiff-string partials, unison strings
   with a slow aftersound, the hammer's felt, the soundboard's weak bass, the knock.
   Everything else is a short grain with a visible cause: a footstep on gravel, stone, wood, snow or asphalt, a drop, a
   bubble, a weir's wash, a waterfall's many drops, a bronze temple bell, a crow, the wooden clappers. There are no loops and
   no noise beds: a grain is a few tens of milliseconds to a few seconds long (the bell: half a minute), and audio.js
   scatters them in time.
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
     the natural sounds of Kyoto
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
  /* a damped, unglided resonance: a heel on a slab, a board's knock, a bronze's thump */
  const tock = (b, at, f, amp, tau) => ring(b, at, f, amp, { d: 1 / tau, xi: 0, len: tau * 7 });
  const log = (lo, hi) => lo * Math.pow(hi / lo, rnd());
  /* a crowd of tiny impacts: pebbles, ice crystals, dry leaves. n of them over `span` seconds, thickest at the start
     (front: how strongly); each one rings (tock) or is a tick of band-limited noise (o.noise) */
  function crunch(b, at, n, span, amp, fLo, fHi, tLo, tHi, o = {}) {
    const front = o.front ?? 2.5;
    for (let k = 0; k < n; k++) {
      const t = (span * -Math.log(1 - rnd() * (1 - Math.exp(-front)))) / front, f = log(fLo, fHi), tau = tLo + (tHi - tLo) * rnd();
      const a = amp * Math.pow(0.15 + rnd(), 2) * (rnd() < 0.08 ? 2.2 : 1);
      if (o.noise) burst(b, at + t * R, f, o.q ?? 1.1, tau, a, 0.0003); else tock(b, at + t * R, f, a, tau);
    }
  }
  /* high-pass (and low-pass), fade the ends, normalise the peak (or the loudness: o.rms); o.eqp fades with sin/cos so that
     two grains laid end to end keep a steady power. A pair of channels shares one gain. */
  function filt(b, hp, lp) {
    const n = b.length, out = new Float32Array(n), h1 = biquad('hp', hp, 0.7, R), h2 = biquad('hp', hp, 0.7, R), l1 = lp ? biquad('lp', lp, 0.7, R) : null;
    let pk = 1e-9, e = 0;
    for (let i = 0; i < n; i++) { let x = h2(h1(b[i])); if (l1) x = l1(x); if (!Number.isFinite(x)) x = 0; out[i] = x; e += x * x; if (Math.abs(x) > pk) pk = Math.abs(x); }
    return { out, pk, e };
  }
  function finish(chs, o = {}) {
    const hp = o.hp || 180, lp = o.lp || 0, F = (Array.isArray(chs) ? chs : [chs]).map((b) => filt(b, hp, lp)), n = F[0].out.length;
    let pk = 1e-9, e = 0; for (const f of F) { pk = Math.max(pk, f.pk); e += f.e; }
    const peak = o.peak ?? 0.9, g = o.rms ? Math.min(o.rms / Math.sqrt(e / (n * F.length)), 0.95 / pk) : peak / pk;
    const fin = Math.floor((o.fin ?? 0.0004) * R), fout = Math.min(n >> 1, Math.floor((o.fout ?? 0.02) * R));
    for (const f of F) {
      const out = f.out;
      for (let i = 0; i < n; i++) {
        let s = out[i] * g;
        if (i < fin) s *= o.eqp ? Math.sin((Math.PI / 2) * (i / fin)) : i / fin;
        if (i > n - fout) { const u = (i - (n - fout)) / fout; s *= o.eqp ? Math.cos((Math.PI / 2) * u) : 0.5 + 0.5 * Math.cos(Math.PI * u); }
        out[i] = s;
      }
    }
    return { rate: R, data: F.map((f) => f.out) };
  }

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
  /* a small stream over stones, a canal's overflow: a few quick gurgles that climb in pitch, a spatter of tiny bubbles, now and then a drop */
  function trickle() {
    R = 32000; const T = 0.95, b = new Float64Array(Math.floor(T * R)), n = 4 + Math.floor(rnd() * 5);
    let t = 0.004;
    for (let k = 0; k < n; k++) { const f = log(420, 2400); ring(b, t * R, f, (0.3 + 0.7 * rnd()) * Math.pow(f / 900, -0.3), { xi: 0.15 + 0.35 * rnd(), d: damp(f) * 0.85 }); t += 0.035 + 0.13 * rnd(); }
    cloud(b, 0.01 * R, 16 + Math.floor(14 * rnd()), 0.55, 1200, 5200, 0.11, 1.2, 1.8);
    if (rnd() < 0.6) { const at = (0.15 + 0.5 * rnd()) * R, f = log(1500, 3400); burst(b, at, 3600, 1.2, 0.001, 0.2); ring(b, at + 4, f, 0.6, { xi: 0.1 + 0.2 * rnd(), d: damp(f) * 0.7 }); }
    return finish(b, { hp: 250, lp: 8500, peak: 0.75, fout: 0.12 });
  }
  /* water pouring over a weir: a surge of froth that swells and thins, the low thump of the fall into the pool, a few big glugs;
     a stereo pair (the weir is wide) that shares its low thump */
  function wash() {
    R = 32000; const T = 2.3, L = new Float64Array(Math.floor(T * R)), Rr = new Float64Array(Math.floor(T * R));
    const rise = 0.25 + 0.15 * rnd(), tau = 0.55 + 0.35 * rnd(), dens = (t) => (t < rise ? 0.2 + 0.8 * Math.sin((Math.PI * t) / (2 * rise)) : Math.exp(-(t - rise) / tau));
    const fp = log(100, 170);
    for (const b of [L, Rr]) tock(b, 6, fp, 0.45, 0.28);
    for (const b of [L, Rr]) {
      for (let k = 0, c = 1500 * T; k < c; k++) {
        const t = rnd() * T; if (rnd() > dens(t)) continue;
        const f = log(700, 6500); ring(b, t * R, f, 0.06 * (0.25 + rnd()) * Math.pow(f / 1500, -0.4));
      }
      for (let k = 0, c = 3 + Math.floor(rnd() * 4); k < c; k++) { const f = log(220, 700); ring(b, (rise * 0.5 + rnd() * 0.9) * R, f, 0.16 + 0.2 * rnd(), { xi: 0.12 + 0.25 * rnd(), d: damp(f) * 0.85 }); }
    }
    return finish([L, Rr], { hp: 90, lp: 8500, peak: 0.8, fout: 0.45 });
  }
  /* a small waterfall: many many drops. Every channel is its own random rain of bubbles — thousands a second, small and bright
     ones most, a hundred mid-sized ones, a few deep ones from the basin — plus the little spats of spray; the density breathes
     a little. Equal-power fades, so that the grains overlap into a steady fall without a seam. Stereo. */
  function fall() {
    R = 32000; const T = 3.4, N = Math.floor(T * R), chs = [new Float64Array(N), new Float64Array(N)];
    for (const b of chs) {
      const p1 = TAU * rnd(), p2 = TAU * rnd(), mod = (t) => 1 + 0.18 * Math.sin(TAU * 0.37 * t + p1) + 0.12 * Math.sin(TAU * 1.3 * t + p2);
      for (let k = 0, c = 900 * T * 1.4; k < c; k++) { const t = rnd() * T; if (rnd() * 1.4 > mod(t)) continue; const f = log(1100, 7500); ring(b, t * R, f, 0.05 * (0.3 + rnd()) * Math.pow(f / 1500, -0.4)); }
      for (let k = 0, c = 48 * T; k < c; k++) { const f = log(350, 1100); ring(b, rnd() * T * R, f, 0.2 * (0.3 + rnd()), { xi: 0.15 + 0.25 * rnd(), d: damp(f) * 0.85 }); }
      for (let k = 0, c = 11 * T; k < c; k++) { const f = log(130, 330); ring(b, rnd() * T * R, f, 0.32 * (0.4 + rnd()), { xi: 0.15 + 0.2 * rnd(), d: damp(f) * 0.9 }); }
      for (let k = 0, c = 16 * T; k < c; k++) burst(b, rnd() * T * R, log(2500, 5200), 0.8, 0.005 + 0.01 * rnd(), 0.09 * (0.4 + rnd()));
    }
    return finish(chs, { hp: 110, lp: 9000, rms: 0.12, fin: 0.7, fout: 0.7, eqp: true });
  }

  /* ---- a person walking ---- */
  /* gravel in a temple courtyard: the weight settling, then a crowd of small stones shifting and clicking against each other
     (a few bigger ones knocking), a slide; the forefoot comes down a tenth of a second later with a smaller crunch */
  function gravel() {
    R = 32000; const b = new Float64Array(Math.floor(0.5 * R)), w = 0.8 + 0.4 * rnd();
    tock(b, 3, log(85, 130), 0.9 * w, 0.035);
    crunch(b, 4, 70 + Math.floor(40 * rnd()), 0.17, 0.5 * w, 1300, 6500, 0.0006, 0.0018, { front: 2.2 });
    crunch(b, 4, 12, 0.12, 0.7 * w, 600, 1400, 0.002, 0.006, { front: 1.5 });
    burst(b, 5, 2600, 0.5, 0.03, 0.12, 0.005);
    const t = (0.1 + 0.04 * rnd()) * R;
    tock(b, t, log(95, 140), 0.45, 0.025); crunch(b, t, 36, 0.12, 0.38, 1300, 6000, 0.0006, 0.0016, { front: 2.5 });
    return finish(b, { hp: 120, lp: 9000, peak: 0.85, fout: 0.06 });
  }
  /* a leather heel on a flagstone: a soft click, the slab's short hollow tock, a little scuff; the forefoot follows */
  function stone() {
    R = 32000; const b = new Float64Array(Math.floor(0.3 * R)), f = log(180, 250);
    burst(b, 2, log(2300, 3300), 1.3, 0.0018, 0.3, 0.0003);
    tock(b, 3, f, 1, 0.02); tock(b, 3, f * 2.3, 0.5, 0.012); tock(b, 3, f * 4.1 * (0.9 + 0.2 * rnd()), 0.22, 0.007);
    burst(b, 4, log(1800, 2800), 0.8, 0.02, 0.07, 0.004);
    crunch(b, 4, 6, 0.04, 0.1, 2500, 6000, 0.0004, 0.001);
    const t = (0.085 + 0.03 * rnd()) * R; tock(b, t, f * 1.3, 0.38, 0.016); burst(b, t, 2600, 1.2, 0.0016, 0.14, 0.0003);
    return finish(b, { hp: 150, lp: 6500, peak: 0.8, fout: 0.04 });
  }
  /* a heel on a wooden floor or a veranda: the board's own hollow knock (a low mode and its overtones, ringing a tenth of a second),
     the click of the heel, a loose neighbour plank; the forefoot knocks a little higher */
  function wood() {
    R = 32000; const b = new Float64Array(Math.floor(0.45 * R)), f1 = log(105, 170);
    tock(b, 3, f1, 1, 0.075); tock(b, 3, f1 * 2.35, 0.5, 0.045); tock(b, 3, f1 * 4.2, 0.22, 0.02); tock(b, 3, f1 * 6.5, 0.1, 0.012);
    burst(b, 2, log(1700, 2600), 1.2, 0.0018, 0.32, 0.0003);
    ring(b, 3, log(380, 620), 0.18, { d: 1 / 0.05, xi: 0, len: 0.3 });
    const t = (0.1 + 0.03 * rnd()) * R, f2 = f1 * 1.18;
    tock(b, t, f2, 0.55, 0.06); tock(b, t, f2 * 2.35, 0.25, 0.035); burst(b, t, 2200, 1.2, 0.0016, 0.16, 0.0003);
    return finish(b, { hp: 70, lp: 6000, peak: 0.8, fout: 0.08 });
  }
  /* cold dry snow: a muffled thud, then ice crystals breaking under the weight (a dense, soft crackle of low ticks), and
     a squeak, a short rising friction tone, as the foot twists; the forefoot makes a second, smaller crunch */
  function snow() {
    R = 32000; const b = new Float64Array(Math.floor(0.55 * R)), w = 0.8 + 0.4 * rnd();
    tock(b, 3, log(70, 100), 0.55 * w, 0.04);
    crunch(b, 4, 80, 0.22, 0.4 * w, 450, 2600, 0.002, 0.006, { noise: true, q: 1.0, front: 1.5 });
    for (let k = 0, c = 1 + (rnd() < 0.5 ? 1 : 0); k < c; k++) { const f = 2100 + 900 * rnd(); ring(b, (0.01 + 0.06 * rnd()) * R, f, 0.16 + 0.1 * rnd(), { d: 1 / 0.035, xi: 0.25, len: 0.25 }); }
    const t = (0.11 + 0.04 * rnd()) * R;
    tock(b, t, log(70, 100), 0.3 * w, 0.035); crunch(b, t, 45, 0.15, 0.3 * w, 450, 2600, 0.002, 0.005, { noise: true, q: 1.0, front: 1.8 });
    return finish(b, { hp: 120, lp: 6500, peak: 0.8, fout: 0.08 });
  }
  /* a shoe on asphalt: a dull tap, a hint of grit, a short scuff; the forefoot a little behind */
  function asphalt() {
    R = 32000; const b = new Float64Array(Math.floor(0.3 * R)), f = log(150, 210);
    burst(b, 2, log(2000, 3200), 1.0, 0.0015, 0.28, 0.0003);
    tock(b, 3, f, 1, 0.014); tock(b, 3, f * 2.1, 0.4, 0.008);
    crunch(b, 4, 14, 0.05, 0.22, 2000, 6000, 0.0004, 0.001);
    burst(b, 5, 1800, 0.6, 0.02, 0.09, 0.004);
    const t = (0.09 + 0.03 * rnd()) * R; tock(b, t, f * 1.25, 0.4, 0.012); burst(b, t, 2400, 1.0, 0.0014, 0.1, 0.0003); crunch(b, t, 5, 0.03, 0.12, 2000, 5000, 0.0004, 0.001);
    return finish(b, { hp: 140, lp: 7000, peak: 0.8, fout: 0.04 });
  }
  /* soil, grass, moss: a dull thud, a soft brush of blades, a few crumbs */
  function soft() {
    R = 32000; const b = new Float64Array(Math.floor(0.35 * R));
    tock(b, 3, log(80, 125), 1, 0.03); burst(b, 3, log(1100, 1800), 0.5, 0.045, 0.22, 0.012);
    crunch(b, 6, 8, 0.1, 0.1, 1500, 4000, 0.0008, 0.002, { noise: true });
    const t = (0.1 + 0.03 * rnd()) * R; tock(b, t, log(85, 130), 0.4, 0.03); burst(b, t, 1400, 0.5, 0.035, 0.1, 0.01);
    return finish(b, { hp: 90, lp: 5000, peak: 0.75, fout: 0.07 });
  }
  /* dry fallen leaves in a wood: a soft thud and a crackle of brittle ticks with a rustle under it */
  function leaves() {
    R = 32000; const b = new Float64Array(Math.floor(0.5 * R));
    tock(b, 3, log(80, 120), 0.6, 0.035);
    crunch(b, 4, 38, 0.28, 0.55, 2200, 7500, 0.001, 0.003, { noise: true, q: 1.5, front: 1.2 });
    burst(b, 5, 3500, 0.5, 0.05, 0.14, 0.01);
    const t = (0.11 + 0.03 * rnd()) * R; tock(b, t, log(85, 130), 0.3, 0.03); crunch(b, t, 22, 0.18, 0.4, 2200, 7000, 0.001, 0.003, { noise: true, q: 1.5, front: 1.5 });
    return finish(b, { hp: 150, lp: 9500, peak: 0.8, fout: 0.08 });
  }

  /* ---- a temple bell ---- */
  /* a bonsho, struck on the outside with a swinging beam: the beam's thump and the low thud of the bronze, a bright cluster
     of quickly dying metal modes, then the slow bloom of the hum (a deep fundamental; its first overtone near the octave; a
     few more partials that are not harmonic), each one a pair of oscillations a fraction of a hertz apart, so that it beats
     (the "wan, wan, wan") as it dies over half a minute. [ratio to the fundamental, amplitude, 60 dB decay (s), beat (Hz), bloom (s)] */
  const MODES = [[1.0, 1.0, 45, 0.42, 0.16], [2.02, 0.9, 34, 0.78, 0.09], [2.77, 0.4, 21, 1.15, 0.06], [3.46, 0.5, 16, 1.4, 0.05], [4.13, 0.3, 12, 0.95, 0.04],
    [5.34, 0.22, 8.7, 1.5, 0.03], [6.6, 0.15, 6.2, 1.9, 0.03], [8.1, 0.1, 4.2, 2.3, 0.02], [9.9, 0.07, 3, 2.7, 0.02], [12.2, 0.05, 2, 3.1, 0.02]];
  function bell(id) {
    R = 16000;
    const [f0, k, dur] = [[73.4, 1.0, 56], [98.0, 0.86, 46], [123.5, 0.72, 38]][id];     /* D2, G2, B2: three sizes */
    const N = Math.floor(dur * R), b = new Float64Array(N);
    for (const [r, a, t60, beat, atk] of MODES) {
      const f = f0 * r * (1 + 0.0012 * gauss()), d = 6.908 / (t60 * k);
      for (const [df, kk, dm] of [[0, 1, 1], [beat * (0.8 + 0.4 * rnd()), 0.8, 1.05]]) {
        const w = (TAU * (f + df)) / R, ph = rnd() * TAU, g = a * kk, dd = d * dm, life = Math.min(N, Math.ceil((Math.log(g / 1e-4) / dd) * R));
        for (let i = 0; i < life; i++) b[i] += g * Math.sin(w * i + ph) * Math.exp((-dd * i) / R) * (1 - Math.exp((-i / R) / atk));
      }
    }
    tock(b, 0, f0 * 0.84, 0.8, 0.09);
    burst(b, 0, log(180, 260), 0.7, 0.03, 0.9, 0.002); burst(b, 0, 1500, 0.8, 0.006, 0.2, 0.0006);
    for (const r of [2.3, 3.7, 5.2, 7.6]) tock(b, 0, f0 * r * (1 + 0.01 * gauss()), 0.4 / Math.sqrt(r), 0.28 / Math.sqrt(r));
    return finish(b, { hp: 35, peak: 0.8, fin: 0.002, fout: 1.2 });
  }

  /* ---- a crow, far away ---- */
  /* kaa, kaa: a pulse-train voice (harmonics falling off gently) whose pitch sags through the call, roughened by a fast amplitude
     flutter, with a little breath, and shaped by three vowel-like resonances; two to four calls */
  function crow() {
    R = 22050; const T = 1.9, b = new Float64Array(Math.floor(T * R)), caws = 2 + (rnd() < 0.55 ? 1 : 0) + (rnd() < 0.2 ? 1 : 0);
    const fm = [biquad('bp', 850, 2.2, R), biquad('bp', 1500, 3, R), biquad('bp', 2900, 3, R)];
    let t0 = 0.05, ph = 0; const base = 500 + 130 * rnd();
    for (let c = 0; c < caws; c++) {
      const dur = 0.26 + 0.13 * rnd(), fa = base * (1 - 0.03 * c) * (0.96 + 0.08 * rnd()), n = Math.floor(dur * R), i0 = Math.floor(t0 * R), flut = 78 + 20 * rnd();
      for (let i = 0; i < n && i0 + i < b.length; i++) {
        const t = i / R, u = i / n, f = fa * (1.05 - 0.3 * u + 0.035 * Math.sin(TAU * 9 * t));
        ph += (TAU * f) / R;
        let s = 0; for (let h = 1, hm = Math.min(30, Math.floor(6000 / f)); h <= hm; h++) s += Math.sin(h * ph) / Math.pow(h, 0.9);
        const env = Math.min(1, i / (0.018 * R)) * (u < 0.7 ? 1 : Math.pow(Math.cos(((u - 0.7) / 0.3) * Math.PI / 2), 2)) * (1 - 0.3 * u);
        const x = (s * (1 - 0.5 * (0.5 + 0.5 * Math.sin(TAU * flut * t))) + 0.9 * (rnd() * 2 - 1)) * env;
        b[i0 + i] += 0.25 * x + fm[0](x) * 0.9 + fm[1](x) * 0.8 + fm[2](x) * 0.45;
      }
      t0 += dur + 0.16 + 0.12 * rnd();
    }
    return finish(b, { hp: 250, lp: 5000, peak: 0.8, fout: 0.08 });
  }

  /* ---- wooden clappers (hyoshigi): two blocks of hard wood struck together — a dry, bright, ringing "kan" ---- */
  function clap() {
    R = 32000; const b = new Float64Array(Math.floor(0.4 * R)), f = log(1250, 1800);
    tock(b, 3, f, 1, 0.014); tock(b, 3, f * 2.42, 0.55, 0.008); tock(b, 3, f * 4.3, 0.28, 0.004); tock(b, 3, f * 0.5, 0.35, 0.02);
    burst(b, 2, 3600, 0.9, 0.0018, 0.4, 0.0002);
    return finish(b, { hp: 300, lp: 9000, peak: 0.85, fout: 0.06 });
  }

  /* how many variants of each grain, and how to make them */
  const MAKERS = { drip, bubble, trickle, wash, fall, gravel, stone, wood, snow, asphalt, soft, leaves, crow, clap, bell: null };
  const COUNTS = { drip: 12, bubble: 8, trickle: 8, wash: 6, fall: 4, gravel: 10, stone: 8, wood: 8, snow: 10, asphalt: 8, soft: 6, leaves: 6, crow: 6, clap: 4, bell: 3 };
  const KINDS = Object.keys(COUNTS);
  function sfx(kind, id) {
    seed = 1013 + KINDS.indexOf(kind) * 7919 + id * 104729;
    for (let i = 0; i < 5; i++) rnd();
    const g = kind === 'bell' ? bell(id) : MAKERS[kind]();
    return { kind, id, rate: g.rate, data: g.data };
  }
  return { note, sfx, COUNTS };
}
