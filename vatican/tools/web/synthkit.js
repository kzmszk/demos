/* The piano and water synthesis from ALOFT (demos/aloft), unchanged except for a fountain sound. */
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

  /* ---------- water: synthesised once, periodic so it loops without a seam ---------- */
  function biquad(type, f, q, rate) {
    const w = (2 * Math.PI * f) / rate, cs = Math.cos(w), al = Math.sin(w) / (2 * q), a0 = 1 + al;
    let b0, b1, b2;
    if (type === 'bp') { b0 = al; b1 = 0; b2 = -al; }
    else if (type === 'hp') { b0 = (1 + cs) / 2; b1 = -(1 + cs); b2 = (1 + cs) / 2; }
    else { b0 = (1 - cs) / 2; b1 = 1 - cs; b2 = (1 - cs) / 2; }
    const B0 = b0 / a0, B1 = b1 / a0, B2 = b2 / a0, A1 = (-2 * cs) / a0, A2 = (1 - al) / a0;
    let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    return (x) => { const y = B0 * x + B1 * x1 + B2 * x2 - A1 * y1 - A2 * y2; x2 = x1; x1 = x; y2 = y1; y1 = y; return y; };
  }
  /* run a filter chain over noise twice around the loop, so the end flows into the start */
  function loopNoise(N, chain) {
    const out = new Float32Array(N), pre = Math.min(N, 20000);
    for (let i = N - pre; i < N; i++) chain(rnd() * 2 - 1, i);
    for (let i = 0; i < N; i++) out[i] = chain(rnd() * 2 - 1, i);
    return out;
  }
  /* a splash: a short burst of band-limited noise; thousands of them are what make noise sound wet */
  function splash(buf, N, rate, at, f, len, amp) {
    const bp = biquad('bp', f, 1.4, rate), n = Math.floor(len * rate), atk = Math.max(4, Math.floor(n * 0.08));
    for (let i = 0; i < n; i++) buf[(at + i) % N] += bp(rnd() * 2 - 1) * amp * Math.min(1, i / atk) * Math.pow(1 - i / n, 2);
  }
  /* a slosh: a wash of water swelling and draining away, its pitch falling as it recedes (a swept state-variable filter) */
  function slosh(buf, N, rate, at, f, rise, fall, amp) {
    const n = Math.floor((rise + fall * 3) * rate);
    let low = 0, band = 0;
    for (let i = 0; i < n; i++) {
      const t = i / rate, env = t < rise ? 0.5 - 0.5 * Math.cos((Math.PI * t) / rise) : Math.exp(-(t - rise) / fall);
      const f1 = 2 * Math.sin((Math.PI * f * (1 - 0.35 * Math.min(1, t / (rise + fall)))) / rate);
      low += f1 * band; const high = rnd() * 2 - 1 - low - 1.1 * band; band += f1 * high;
      buf[(at + i) % N] += amp * env * (band * 0.8 + high * 0.15);
    }
  }
  /* a gas bubble's ring (Minnaert): a decaying sine whose pitch rises as it nears the surface */
  function bubble(buf, N, rate, at, f, amp) {
    const d = 0.043 * f + 0.0014 * Math.pow(f, 1.5), rise = 0.1 + 0.4 * rnd(), len = Math.min(Math.ceil((7 / d) * rate), 4000);
    let ph = 0;
    for (let i = 0; i < len; i++) {
      const t = i / rate, fi = f * (1 + rise * d * t);
      ph += (2 * Math.PI * fi) / rate;
      buf[(at + i) % N] += amp * Math.sin(ph) * Math.exp(-d * t) * Math.min(1, i / 8);
    }
  }
  const hpass = (buf, f, rate) => { const h1 = biquad('hp', f, 0.7, rate), h2 = biquad('hp', f, 0.7, rate), N = buf.length; for (let i = N - Math.min(N, 20000); i < N; i++) h2(h1(buf[i])); for (let i = 0; i < N; i++) buf[i] = h2(h1(buf[i])); return buf; };
  function water(kind) {
    const rate = 32000;
    if (kind === 'falls') {
      /* a big fall heard from the air: a dense spray of splashes over a broad wash, threaded with bubbles */
      const N = rate * 7, chans = [];
      for (let c = 0; c < 2; c++) {
        seed = 77 + c * 31;
        const body = biquad('bp', 520, 0.45, rate), air = biquad('bp', 3000, 0.6, rate);
        const s = loopNoise(N, (x) => body(x) * 0.55 + air(x) * 0.22);
        for (let k = 0; k < 7 * 1400; k++) splash(s, N, rate, Math.floor(rnd() * N), 250 * Math.pow(24, rnd()), 0.006 + 0.04 * rnd(), 0.5 * Math.pow(rnd(), 1.5));
        for (let k = 0; k < 7 * 500; k++) bubble(s, N, rate, Math.floor(rnd() * N), 350 + Math.pow(rnd(), 2) * 2600, 0.04 * (0.3 + rnd()));
        chans.push(hpass(s, 140, rate));
      }
      return norm({ kind, rate, data: chans }, 0.2);
    }
    if (kind === 'fountain') {
      /* a fountain: water falling in sheets from the bowls into the basin — splashes and bubbles, no roar */
      const N = rate * 6, chans = [];
      for (let c = 0; c < 2; c++) {
        seed = 911 + c * 23;
        const air = biquad('bp', 2600, 0.7, rate), body = biquad('bp', 900, 0.6, rate);
        const s = loopNoise(N, (x) => air(x) * 0.12 + body(x) * 0.1);
        for (let k = 0; k < 6 * 1100; k++) splash(s, N, rate, Math.floor(rnd() * N), 600 * Math.pow(10, rnd()), 0.004 + 0.02 * rnd(), 0.32 * Math.pow(rnd(), 1.6));
        for (let k = 0; k < 6 * 260; k++) bubble(s, N, rate, Math.floor(rnd() * N), 500 + rnd() * 2400, 0.03 * (0.3 + rnd()));
        chans.push(hpass(s, 220, rate));
      }
      return norm({ kind, rate, data: chans }, 0.16);
    }
    if (kind === 'surf') {
      /* waves breaking on the reef: a swell, the crash, then a long fizzing wash; two of them around the loop */
      const N = rate * 13, chans = [];
      for (let c = 0; c < 2; c++) {
        seed = 5 + c * 13;
        const body = biquad('bp', 480, 0.5, rate), fizz = biquad('bp', 4600, 0.8, rate);
        const waves = [[0.4 + c * 0.25, 1], [6.9 + c * 0.2, 0.75]];
        const env = (t) => {
          let e = 0, w = 0;
          for (const [t0, a] of waves) for (const p of [-13, 0, 13]) {
            const u = t - t0 - p;
            if (u > -1.6 && u < 0) e += a * Math.pow(1 + u / 1.6, 2.5) * 0.6;
            else if (u >= 0 && u < 9) { e += a * (0.6 + 0.4 * Math.exp(-u * 3)) * Math.exp(-u / 1.4); w += a * Math.exp(-u / 2.6) * (u < 0.15 ? u / 0.15 : 1); }
          }
          return [e, w];
        };
        const s = loopNoise(N, (x, i) => { const [e, w] = env(i / rate); return body(x) * e * 0.8 + fizz(x) * w * 0.25; });
        for (let k = 0; k < 13 * 900; k++) {
          const t = rnd() * 13, [e, w] = env(t), at = Math.floor(t * rate);
          if (rnd() < e) splash(s, N, rate, at, 300 * Math.pow(12, rnd()), 0.01 + 0.05 * rnd(), 0.35 * e * rnd());
          if (rnd() < w * 0.8) splash(s, N, rate, at, 2500 + 5000 * rnd(), 0.002 + 0.006 * rnd(), 0.5 * w * rnd());
          if (rnd() < w * 0.25) bubble(s, N, rate, at, 900 + rnd() * 3000, 0.035 * rnd());
        }
        chans.push(hpass(s, 160, rate));
      }
      return norm({ kind, rate, data: chans }, 0.16);
    }
    /* 'lap': little waves against ice or a hull: a soft wash swelling and draining away, droplets, and the
       glug of air after. No thump — a short low burst is what a distant firework sounds like */
    const N = rate * 13, chans = [];
    for (let c = 0; c < 2; c++) {
      seed = 301 + c * 17;
      const s = new Float32Array(N);
      for (let k = 0; k < 13 * 70; k++) splash(s, N, rate, Math.floor(rnd() * N), 1200 + rnd() * 4500, 0.004 + 0.01 * rnd(), 0.05 * rnd());
      let t = rnd() * 0.6;
      while (t < 13) {
        const at = Math.floor(t * rate), a = 0.35 + 0.65 * rnd();
        slosh(s, N, rate, at, 900 + rnd() * 900, 0.07 + 0.09 * rnd(), 0.22 + 0.3 * rnd(), a * 0.55);
        for (let k = 0; k < 5; k++) splash(s, N, rate, at + Math.floor((0.03 + rnd() * 0.14) * rate), 2000 + rnd() * 4000, 0.004 + 0.012 * rnd(), a * 0.22 * rnd());
        for (let k = 0; k < 3 + rnd() * 7; k++) bubble(s, N, rate, at + Math.floor((0.12 + rnd() * 0.45) * rate), 450 + rnd() * 1300, 0.035 * a * rnd());
        t += 0.6 + rnd() * 1.6;
      }
      chans.push(hpass(s, 260, rate));
    }
    return norm({ kind, rate, data: chans }, 0.12);
  }
  function norm(w, target) {
    let e = 0, n = 0;
    for (const d of w.data) for (let i = 0; i < d.length; i++) { e += d[i] * d[i]; n++; }
    const g = target / (Math.sqrt(e / n) || 1);
    for (const d of w.data) for (let i = 0; i < d.length; i++) d[i] *= g;
    return w;
  }
  return { note, water };
}
