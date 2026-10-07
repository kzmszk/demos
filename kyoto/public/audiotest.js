// web/synthkit.js
function synthKit() {
  const clamp2 = (x, a, b) => Math.min(b, Math.max(a, x));
  let seed = 1;
  const rnd = () => (seed = seed * 16807 % 2147483647) / 2147483647;
  const gauss = () => {
    let s = 0;
    for (let i = 0; i < 4; i++) s += rnd();
    return (s - 2) * 1.7;
  };
  function note(m, need = 99) {
    seed = 1e3 + m * 7;
    const rate = m < 50 ? 22050 : 32e3;
    const f0 = 440 * Math.pow(2, (m - 69) / 12);
    const B = m >= 48 ? Math.pow(10, -3.7 + 0.035 * (m - 48)) : Math.pow(10, -3.7 + 0.011 * (48 - m));
    const dur = Math.max(1.2, Math.min(clamp2(11 - (m - 24) * 0.115, 2.6, 11), need + 0.6));
    const N = Math.floor(dur * rate), acc = new Float64Array(N);
    const b1 = 0.2 + 0.35 * Math.pow(2, (m - 60) / 12), b3 = 3e-7;
    const fmax = Math.min(rate * 0.45, 12e3);
    const beta = 0.122;
    const fc = 900 * Math.pow(2, (m - 60) / 24);
    const strings = m < 34 ? 1 : m < 46 ? 2 : 3;
    for (let n = 1; ; n++) {
      const fn = n * f0 * Math.sqrt(1 + B * n * n);
      if (fn > fmax) break;
      let a = Math.abs(Math.sin(Math.PI * n * beta)) + 0.05;
      a *= 1 / (1 + fn / fc * (fn / fc));
      a *= fn * fn / (fn * fn + 110 * 110);
      if (a < 1e-5) continue;
      const aft = b1 + b3 * fn * fn, prompt = aft * 2.6 + 0.3;
      const comps = [[0.6, prompt, 0]];
      if (strings > 1) comps.push([0.32, prompt * 1.12, 19e-5 * (1 + 0.3 * gauss())]);
      if (strings > 2) comps.push([0.22, prompt * 0.9, -14e-5 * (1 + 0.3 * gauss())]);
      comps.push([0.16, aft, 8e-5 * gauss()]);
      for (const [k, alpha, det] of comps) {
        const amp = a * k, w = 2 * Math.PI * fn * (1 + det) / rate, r = Math.exp(-alpha / rate);
        const life = Math.min(N, Math.ceil(Math.log(amp / 2e-6) / alpha * rate));
        if (life < 4) continue;
        const c1 = 2 * r * Math.cos(w), c2 = r * r;
        let y1 = 0, y0 = amp * r * Math.sin(w);
        acc[1] += y0;
        for (let i = 2; i < life; i++) {
          const y = c1 * y0 - c2 * y1;
          y1 = y0;
          y0 = y;
          acc[i] += y;
        }
      }
    }
    const knock = 0.05 + 0.25 * clamp2((m - 40) / 60, 0, 1);
    for (const [fk, tk] of [[96, 0.05], [143, 0.04], [212, 0.03], [287, 0.025], [415, 0.018], [620, 0.012]]) {
      const w = 2 * Math.PI * fk * (1 + 0.04 * gauss()) / rate, r = Math.exp(-1 / (tk * rate)), c1 = 2 * r * Math.cos(w), c2 = r * r;
      let y1 = 0, y0 = knock * 0.012 * (0.6 + 0.8 * rnd()) * r * Math.sin(w);
      const life = Math.min(N, Math.ceil(tk * 9 * rate));
      for (let i = 1; i < life; i++) {
        const y = c1 * y0 - c2 * y1;
        y1 = y0;
        y0 = y;
        acc[i] += y;
      }
    }
    let e = 0;
    const win = Math.floor(0.35 * rate);
    for (let i = 0; i < win; i++) e += acc[i] * acc[i];
    const rms = Math.sqrt(e / win) || 1, tilt = m < 60 ? 1 + (60 - m) * 4e-3 : 1 - (m - 60) * 6e-3;
    const g = 0.2 * tilt / rms, out = new Float32Array(N), fin = Math.floor(6e-4 * rate), fout = Math.floor(0.25 * rate);
    for (let i = 0; i < N; i++) {
      let s = acc[i] * g;
      if (i < fin) s *= i / fin;
      if (i > N - fout) s *= 0.5 + 0.5 * Math.cos(Math.PI * (i - (N - fout)) / fout);
      out[i] = s;
    }
    return { m, rate, data: [out] };
  }
  const TAU = Math.PI * 2;
  let R = 32e3;
  function biquad(type, f, q, rate) {
    const w = TAU * f / rate, cs = Math.cos(w), al = Math.sin(w) / (2 * q), a0 = 1 + al;
    let b0, b1, b2;
    if (type === "bp") {
      b0 = al;
      b1 = 0;
      b2 = -al;
    } else if (type === "hp") {
      b0 = (1 + cs) / 2;
      b1 = -(1 + cs);
      b2 = (1 + cs) / 2;
    } else {
      b0 = (1 - cs) / 2;
      b1 = 1 - cs;
      b2 = (1 - cs) / 2;
    }
    const B0 = b0 / a0, B1 = b1 / a0, B2 = b2 / a0, A1 = -2 * cs / a0, A2 = (1 - al) / a0;
    let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    return (x) => {
      const y = B0 * x + B1 * x1 + B2 * x2 - A1 * y1 - A2 * y2;
      x2 = x1;
      x1 = x;
      y2 = y1;
      y1 = y;
      return y;
    };
  }
  const damp = (f) => 0.043 * f + 14e-4 * Math.pow(f, 1.5);
  function ring(b, at, f, amp, o = {}) {
    at = Math.floor(at);
    if (at < 0 || at >= b.length) return;
    const d = o.d || damp(f), xi = o.xi ?? 0.1 + 0.4 * rnd();
    const n = Math.min(Math.ceil((o.len || 7 / d) * R), b.length - at);
    let ph = o.ph || 0;
    for (let i = 0; i < n; i++) {
      const t = i / R;
      ph += TAU * f * (1 + xi * d * t) / R;
      b[at + i] += amp * Math.sin(ph) * Math.exp(-d * t) * Math.min(1, i / 6);
    }
  }
  function burst(b, at, f, q, tau, amp, atk = 6e-4) {
    at = Math.floor(at);
    if (at < 0 || at >= b.length) return;
    const bp = biquad("bp", f, q, R), n = Math.min(Math.ceil(tau * 7 * R), b.length - at), a = Math.max(2, Math.floor(atk * R));
    for (let i = 0; i < n; i++) b[at + i] += bp(rnd() * 2 - 1) * amp * Math.min(1, i / a) * Math.exp(-i / (tau * R));
  }
  function cloud(b, at, count, span, fLo, fHi, amp, skew = 1.2, front = 3) {
    for (let k = 0; k < count; k++) {
      const t = span * -Math.log(1 - rnd() * (1 - Math.exp(-front))) / front;
      const f = fLo * Math.pow(fHi / fLo, Math.pow(rnd(), skew));
      ring(b, at + t * R, f, amp * (0.25 + rnd()) * Math.pow(f / 1200, -0.5));
    }
  }
  const tock = (b, at, f, amp, tau) => ring(b, at, f, amp, { d: 1 / tau, xi: 0, len: tau * 7 });
  const log2 = (lo, hi) => lo * Math.pow(hi / lo, rnd());
  function crunch(b, at, n, span, amp, fLo, fHi, tLo, tHi, o = {}) {
    const front = o.front ?? 2.5;
    for (let k = 0; k < n; k++) {
      const t = span * -Math.log(1 - rnd() * (1 - Math.exp(-front))) / front, f = log2(fLo, fHi), tau = tLo + (tHi - tLo) * rnd();
      const a = amp * Math.pow(0.15 + rnd(), 2) * (rnd() < 0.08 ? 2.2 : 1);
      if (o.noise) burst(b, at + t * R, f, o.q ?? 1.1, tau, a, 3e-4);
      else tock(b, at + t * R, f, a, tau);
    }
  }
  function filt(b, hp, lp) {
    const n = b.length, out = new Float32Array(n), h1 = biquad("hp", hp, 0.7, R), h2 = biquad("hp", hp, 0.7, R), l1 = lp ? biquad("lp", lp, 0.7, R) : null;
    let pk = 1e-9, e = 0;
    for (let i = 0; i < n; i++) {
      let x = h2(h1(b[i]));
      if (l1) x = l1(x);
      if (!Number.isFinite(x)) x = 0;
      out[i] = x;
      e += x * x;
      if (Math.abs(x) > pk) pk = Math.abs(x);
    }
    return { out, pk, e };
  }
  function finish(chs, o = {}) {
    const hp = o.hp || 180, lp = o.lp || 0, F = (Array.isArray(chs) ? chs : [chs]).map((b) => filt(b, hp, lp)), n = F[0].out.length;
    let pk = 1e-9, e = 0;
    for (const f of F) {
      pk = Math.max(pk, f.pk);
      e += f.e;
    }
    const peak = o.peak ?? 0.9, g = o.rms ? Math.min(o.rms / Math.sqrt(e / (n * F.length)), 0.95 / pk) : peak / pk;
    const fin = Math.floor((o.fin ?? 4e-4) * R), fout = Math.min(n >> 1, Math.floor((o.fout ?? 0.02) * R));
    for (const f of F) {
      const out = f.out;
      for (let i = 0; i < n; i++) {
        let s = out[i] * g;
        if (i < fin) s *= o.eqp ? Math.sin(Math.PI / 2 * (i / fin)) : i / fin;
        if (i > n - fout) {
          const u = (i - (n - fout)) / fout;
          s *= o.eqp ? Math.cos(Math.PI / 2 * u) : 0.5 + 0.5 * Math.cos(Math.PI * u);
        }
        out[i] = s;
      }
    }
    return { rate: R, data: F.map((f) => f.out) };
  }
  function drip() {
    R = 32e3;
    const b = new Float64Array(Math.floor(0.4 * R));
    const f = log2(1e3, 3200);
    burst(b, 4, 3600, 1.2, 1e-3, 0.3);
    ring(b, 5, f, 1, { xi: 0.1 + 0.2 * rnd(), d: damp(f) * 0.7 });
    if (rnd() < 0.5) ring(b, (0.04 + 0.07 * rnd()) * R, f * (0.6 + 0.3 * rnd()), 0.25 + 0.25 * rnd(), { xi: 0.08 + 0.15 * rnd(), d: damp(f) * 0.8 });
    return finish(b, { hp: 500, peak: 0.8 });
  }
  function bubble() {
    R = 32e3;
    const b = new Float64Array(Math.floor(0.45 * R));
    const f = log2(300, 950);
    ring(b, 6, f, 1, { xi: 0.18 + 0.3 * rnd(), d: damp(f) * 0.85 });
    if (rnd() < 0.4) ring(b, (0.05 + 0.08 * rnd()) * R, f * (1.2 + 0.5 * rnd()), 0.35, { xi: 0.2 });
    return finish(b, { hp: 200, peak: 0.85 });
  }
  function trickle() {
    R = 32e3;
    const T = 0.95, b = new Float64Array(Math.floor(T * R)), n = 4 + Math.floor(rnd() * 5);
    let t = 4e-3;
    for (let k = 0; k < n; k++) {
      const f = log2(420, 2400);
      ring(b, t * R, f, (0.3 + 0.7 * rnd()) * Math.pow(f / 900, -0.3), { xi: 0.15 + 0.35 * rnd(), d: damp(f) * 0.85 });
      t += 0.035 + 0.13 * rnd();
    }
    cloud(b, 0.01 * R, 16 + Math.floor(14 * rnd()), 0.55, 1200, 5200, 0.11, 1.2, 1.8);
    if (rnd() < 0.6) {
      const at = (0.15 + 0.5 * rnd()) * R, f = log2(1500, 3400);
      burst(b, at, 3600, 1.2, 1e-3, 0.2);
      ring(b, at + 4, f, 0.6, { xi: 0.1 + 0.2 * rnd(), d: damp(f) * 0.7 });
    }
    return finish(b, { hp: 250, lp: 8500, peak: 0.75, fout: 0.12 });
  }
  function wash() {
    R = 32e3;
    const T = 2.3, L = new Float64Array(Math.floor(T * R)), Rr = new Float64Array(Math.floor(T * R));
    const rise = 0.25 + 0.15 * rnd(), tau = 0.55 + 0.35 * rnd(), dens = (t) => t < rise ? 0.2 + 0.8 * Math.sin(Math.PI * t / (2 * rise)) : Math.exp(-(t - rise) / tau);
    const fp = log2(100, 170);
    for (const b of [L, Rr]) tock(b, 6, fp, 0.45, 0.28);
    for (const b of [L, Rr]) {
      for (let k = 0, c = 1500 * T; k < c; k++) {
        const t = rnd() * T;
        if (rnd() > dens(t)) continue;
        const f = log2(700, 6500);
        ring(b, t * R, f, 0.06 * (0.25 + rnd()) * Math.pow(f / 1500, -0.4));
      }
      for (let k = 0, c = 3 + Math.floor(rnd() * 4); k < c; k++) {
        const f = log2(220, 700);
        ring(b, (rise * 0.5 + rnd() * 0.9) * R, f, 0.16 + 0.2 * rnd(), { xi: 0.12 + 0.25 * rnd(), d: damp(f) * 0.85 });
      }
    }
    return finish([L, Rr], { hp: 90, lp: 8500, peak: 0.8, fout: 0.45 });
  }
  function fall() {
    R = 32e3;
    const T = 3.4, N = Math.floor(T * R), chs = [new Float64Array(N), new Float64Array(N)];
    for (const b of chs) {
      const p1 = TAU * rnd(), p2 = TAU * rnd(), mod = (t) => 1 + 0.18 * Math.sin(TAU * 0.37 * t + p1) + 0.12 * Math.sin(TAU * 1.3 * t + p2);
      for (let k = 0, c = 900 * T * 1.4; k < c; k++) {
        const t = rnd() * T;
        if (rnd() * 1.4 > mod(t)) continue;
        const f = log2(1100, 7500);
        ring(b, t * R, f, 0.05 * (0.3 + rnd()) * Math.pow(f / 1500, -0.4));
      }
      for (let k = 0, c = 48 * T; k < c; k++) {
        const f = log2(350, 1100);
        ring(b, rnd() * T * R, f, 0.2 * (0.3 + rnd()), { xi: 0.15 + 0.25 * rnd(), d: damp(f) * 0.85 });
      }
      for (let k = 0, c = 11 * T; k < c; k++) {
        const f = log2(130, 330);
        ring(b, rnd() * T * R, f, 0.32 * (0.4 + rnd()), { xi: 0.15 + 0.2 * rnd(), d: damp(f) * 0.9 });
      }
      for (let k = 0, c = 16 * T; k < c; k++) burst(b, rnd() * T * R, log2(2500, 5200), 0.8, 5e-3 + 0.01 * rnd(), 0.09 * (0.4 + rnd()));
    }
    return finish(chs, { hp: 110, lp: 9e3, rms: 0.12, fin: 0.7, fout: 0.7, eqp: true });
  }
  function gravel() {
    R = 32e3;
    const b = new Float64Array(Math.floor(0.5 * R)), w = 0.8 + 0.4 * rnd();
    tock(b, 3, log2(85, 130), 0.9 * w, 0.035);
    crunch(b, 4, 70 + Math.floor(40 * rnd()), 0.17, 0.5 * w, 1300, 6500, 6e-4, 18e-4, { front: 2.2 });
    crunch(b, 4, 12, 0.12, 0.7 * w, 600, 1400, 2e-3, 6e-3, { front: 1.5 });
    burst(b, 5, 2600, 0.5, 0.03, 0.12, 5e-3);
    const t = (0.1 + 0.04 * rnd()) * R;
    tock(b, t, log2(95, 140), 0.45, 0.025);
    crunch(b, t, 36, 0.12, 0.38, 1300, 6e3, 6e-4, 16e-4, { front: 2.5 });
    return finish(b, { hp: 120, lp: 9e3, peak: 0.85, fout: 0.06 });
  }
  function stone() {
    R = 32e3;
    const b = new Float64Array(Math.floor(0.3 * R)), f = log2(180, 250);
    burst(b, 2, log2(2300, 3300), 1.3, 18e-4, 0.3, 3e-4);
    tock(b, 3, f, 1, 0.02);
    tock(b, 3, f * 2.3, 0.5, 0.012);
    tock(b, 3, f * 4.1 * (0.9 + 0.2 * rnd()), 0.22, 7e-3);
    burst(b, 4, log2(1800, 2800), 0.8, 0.02, 0.07, 4e-3);
    crunch(b, 4, 6, 0.04, 0.1, 2500, 6e3, 4e-4, 1e-3);
    const t = (0.085 + 0.03 * rnd()) * R;
    tock(b, t, f * 1.3, 0.38, 0.016);
    burst(b, t, 2600, 1.2, 16e-4, 0.14, 3e-4);
    return finish(b, { hp: 150, lp: 6500, peak: 0.8, fout: 0.04 });
  }
  function wood() {
    R = 32e3;
    const b = new Float64Array(Math.floor(0.45 * R)), f1 = log2(105, 170);
    tock(b, 3, f1, 1, 0.075);
    tock(b, 3, f1 * 2.35, 0.5, 0.045);
    tock(b, 3, f1 * 4.2, 0.22, 0.02);
    tock(b, 3, f1 * 6.5, 0.1, 0.012);
    burst(b, 2, log2(1700, 2600), 1.2, 18e-4, 0.32, 3e-4);
    ring(b, 3, log2(380, 620), 0.18, { d: 1 / 0.05, xi: 0, len: 0.3 });
    const t = (0.1 + 0.03 * rnd()) * R, f2 = f1 * 1.18;
    tock(b, t, f2, 0.55, 0.06);
    tock(b, t, f2 * 2.35, 0.25, 0.035);
    burst(b, t, 2200, 1.2, 16e-4, 0.16, 3e-4);
    return finish(b, { hp: 70, lp: 6e3, peak: 0.8, fout: 0.08 });
  }
  function snow() {
    R = 32e3;
    const b = new Float64Array(Math.floor(0.55 * R)), w = 0.8 + 0.4 * rnd();
    tock(b, 3, log2(70, 100), 0.55 * w, 0.04);
    crunch(b, 4, 80, 0.22, 0.4 * w, 450, 2600, 2e-3, 6e-3, { noise: true, q: 1, front: 1.5 });
    for (let k = 0, c = 1 + (rnd() < 0.5 ? 1 : 0); k < c; k++) {
      const f = 2100 + 900 * rnd();
      ring(b, (0.01 + 0.06 * rnd()) * R, f, 0.16 + 0.1 * rnd(), { d: 1 / 0.035, xi: 0.25, len: 0.25 });
    }
    const t = (0.11 + 0.04 * rnd()) * R;
    tock(b, t, log2(70, 100), 0.3 * w, 0.035);
    crunch(b, t, 45, 0.15, 0.3 * w, 450, 2600, 2e-3, 5e-3, { noise: true, q: 1, front: 1.8 });
    return finish(b, { hp: 120, lp: 6500, peak: 0.8, fout: 0.08 });
  }
  function asphalt() {
    R = 32e3;
    const b = new Float64Array(Math.floor(0.3 * R)), f = log2(150, 210);
    burst(b, 2, log2(2e3, 3200), 1, 15e-4, 0.28, 3e-4);
    tock(b, 3, f, 1, 0.014);
    tock(b, 3, f * 2.1, 0.4, 8e-3);
    crunch(b, 4, 14, 0.05, 0.22, 2e3, 6e3, 4e-4, 1e-3);
    burst(b, 5, 1800, 0.6, 0.02, 0.09, 4e-3);
    const t = (0.09 + 0.03 * rnd()) * R;
    tock(b, t, f * 1.25, 0.4, 0.012);
    burst(b, t, 2400, 1, 14e-4, 0.1, 3e-4);
    crunch(b, t, 5, 0.03, 0.12, 2e3, 5e3, 4e-4, 1e-3);
    return finish(b, { hp: 140, lp: 7e3, peak: 0.8, fout: 0.04 });
  }
  function soft() {
    R = 32e3;
    const b = new Float64Array(Math.floor(0.35 * R));
    tock(b, 3, log2(80, 125), 1, 0.03);
    burst(b, 3, log2(1100, 1800), 0.5, 0.045, 0.22, 0.012);
    crunch(b, 6, 8, 0.1, 0.1, 1500, 4e3, 8e-4, 2e-3, { noise: true });
    const t = (0.1 + 0.03 * rnd()) * R;
    tock(b, t, log2(85, 130), 0.4, 0.03);
    burst(b, t, 1400, 0.5, 0.035, 0.1, 0.01);
    return finish(b, { hp: 90, lp: 5e3, peak: 0.75, fout: 0.07 });
  }
  function leaves() {
    R = 32e3;
    const b = new Float64Array(Math.floor(0.5 * R));
    tock(b, 3, log2(80, 120), 0.6, 0.035);
    crunch(b, 4, 38, 0.28, 0.55, 2200, 7500, 1e-3, 3e-3, { noise: true, q: 1.5, front: 1.2 });
    burst(b, 5, 3500, 0.5, 0.05, 0.14, 0.01);
    const t = (0.11 + 0.03 * rnd()) * R;
    tock(b, t, log2(85, 130), 0.3, 0.03);
    crunch(b, t, 22, 0.18, 0.4, 2200, 7e3, 1e-3, 3e-3, { noise: true, q: 1.5, front: 1.5 });
    return finish(b, { hp: 150, lp: 9500, peak: 0.8, fout: 0.08 });
  }
  const MODES = [
    [1, 1, 45, 0.42, 0.16],
    [2.02, 0.9, 34, 0.78, 0.09],
    [2.77, 0.4, 21, 1.15, 0.06],
    [3.46, 0.5, 16, 1.4, 0.05],
    [4.13, 0.3, 12, 0.95, 0.04],
    [5.34, 0.22, 8.7, 1.5, 0.03],
    [6.6, 0.15, 6.2, 1.9, 0.03],
    [8.1, 0.1, 4.2, 2.3, 0.02],
    [9.9, 0.07, 3, 2.7, 0.02],
    [12.2, 0.05, 2, 3.1, 0.02]
  ];
  function bell(id) {
    R = 16e3;
    const [f0, k, dur] = [[73.4, 1, 56], [98, 0.86, 46], [123.5, 0.72, 38]][id];
    const N = Math.floor(dur * R), b = new Float64Array(N);
    for (const [r, a, t60, beat, atk] of MODES) {
      const f = f0 * r * (1 + 12e-4 * gauss()), d = 6.908 / (t60 * k);
      for (const [df, kk, dm] of [[0, 1, 1], [beat * (0.8 + 0.4 * rnd()), 0.8, 1.05]]) {
        const w = TAU * (f + df) / R, ph = rnd() * TAU, g = a * kk, dd = d * dm, life = Math.min(N, Math.ceil(Math.log(g / 1e-4) / dd * R));
        for (let i = 0; i < life; i++) b[i] += g * Math.sin(w * i + ph) * Math.exp(-dd * i / R) * (1 - Math.exp(-i / R / atk));
      }
    }
    tock(b, 0, f0 * 0.84, 0.8, 0.09);
    burst(b, 0, log2(180, 260), 0.7, 0.03, 0.9, 2e-3);
    burst(b, 0, 1500, 0.8, 6e-3, 0.2, 6e-4);
    for (const r of [2.3, 3.7, 5.2, 7.6]) tock(b, 0, f0 * r * (1 + 0.01 * gauss()), 0.4 / Math.sqrt(r), 0.28 / Math.sqrt(r));
    return finish(b, { hp: 35, peak: 0.8, fin: 2e-3, fout: 1.2 });
  }
  function crow() {
    R = 22050;
    const T = 1.9, b = new Float64Array(Math.floor(T * R)), caws = 2 + (rnd() < 0.55 ? 1 : 0) + (rnd() < 0.2 ? 1 : 0);
    const fm = [biquad("bp", 850, 2.2, R), biquad("bp", 1500, 3, R), biquad("bp", 2900, 3, R)];
    let t0 = 0.05, ph = 0;
    const base = 500 + 130 * rnd();
    for (let c = 0; c < caws; c++) {
      const dur = 0.26 + 0.13 * rnd(), fa = base * (1 - 0.03 * c) * (0.96 + 0.08 * rnd()), n = Math.floor(dur * R), i0 = Math.floor(t0 * R), flut = 78 + 20 * rnd();
      for (let i = 0; i < n && i0 + i < b.length; i++) {
        const t = i / R, u = i / n, f = fa * (1.05 - 0.3 * u + 0.035 * Math.sin(TAU * 9 * t));
        ph += TAU * f / R;
        let s = 0;
        for (let h = 1, hm = Math.min(30, Math.floor(6e3 / f)); h <= hm; h++) s += Math.sin(h * ph) / Math.pow(h, 0.9);
        const env = Math.min(1, i / (0.018 * R)) * (u < 0.7 ? 1 : Math.pow(Math.cos((u - 0.7) / 0.3 * Math.PI / 2), 2)) * (1 - 0.3 * u);
        const x = (s * (1 - 0.5 * (0.5 + 0.5 * Math.sin(TAU * flut * t))) + 0.9 * (rnd() * 2 - 1)) * env;
        b[i0 + i] += 0.25 * x + fm[0](x) * 0.9 + fm[1](x) * 0.8 + fm[2](x) * 0.45;
      }
      t0 += dur + 0.16 + 0.12 * rnd();
    }
    return finish(b, { hp: 250, lp: 5e3, peak: 0.8, fout: 0.08 });
  }
  function clap() {
    R = 32e3;
    const b = new Float64Array(Math.floor(0.4 * R)), f = log2(1250, 1800);
    tock(b, 3, f, 1, 0.014);
    tock(b, 3, f * 2.42, 0.55, 8e-3);
    tock(b, 3, f * 4.3, 0.28, 4e-3);
    tock(b, 3, f * 0.5, 0.35, 0.02);
    burst(b, 2, 3600, 0.9, 18e-4, 0.4, 2e-4);
    return finish(b, { hp: 300, lp: 9e3, peak: 0.85, fout: 0.06 });
  }
  const MAKERS = { drip, bubble, trickle, wash, fall, gravel, stone, wood, snow, asphalt, soft, leaves, crow, clap, bell: null };
  const COUNTS2 = { drip: 12, bubble: 8, trickle: 8, wash: 6, fall: 4, gravel: 10, stone: 8, wood: 8, snow: 10, asphalt: 8, soft: 6, leaves: 6, crow: 6, clap: 4, bell: 3 };
  const KINDS = Object.keys(COUNTS2);
  function sfx(kind, id) {
    seed = 1013 + KINDS.indexOf(kind) * 7919 + id * 104729;
    for (let i = 0; i < 5; i++) rnd();
    const g = kind === "bell" ? bell(id) : MAKERS[kind]();
    return { kind, id, rate: g.rate, data: g.data };
  }
  return { note, sfx, COUNTS: COUNTS2 };
}

// web/audio.js
var clamp = (x, a, b) => Math.min(b, Math.max(a, x));
var lerp = (a, b, t) => a + (b - a) * t;
var sstep = (a, b, x) => {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
var hz = (m) => 440 * Math.pow(2, (m - 69) / 12);
var num = (x, d = 0) => typeof x === "number" && Number.isFinite(x) ? x : d;
var idNum = (id) => {
  if (typeof id === "string") {
    let h = 0;
    for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) % 100003;
    return h;
  }
  return Math.abs(Math.floor(num(id, 0)));
};
var sleep = (ms) => new Promise((r) => setTimeout(r, ms));
var PPQ = 48;
function lcg(seed) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => (s = s * 16807 % 2147483647) / 2147483647;
}
function prepare(mv, idx) {
  const total = mv.total_beats, tm = mv.tempo_map && mv.tempo_map.length ? mv.tempo_map : [[0, mv.bpm]];
  const bb = Array.from(new Set(mv.bar_beats)).sort((a, b) => a - b), reg = [];
  bb.forEach((a, i) => {
    const z = i + 1 < bb.length ? bb[i + 1] : total;
    if (z - a >= 1) reg.push([a, z]);
  });
  const ctr = [], fac = [];
  reg.forEach(([a, z], i) => {
    let f = [1, 0.985, 0.985, 1.04][i % 4];
    if (i % 8 === 7) f *= 1.03;
    if (i % 16 === 15) f *= 1.05;
    if (i === reg.length - 1) f *= 1.22;
    else if (i === reg.length - 2) f *= 1.07;
    ctr.push((a + z) / 2);
    fac.push(f);
  });
  const n = Math.ceil(total * PPQ) + PPQ, cum = new Float64Array(n + 1);
  let seg = 0, ti = 0;
  for (let j = 0; j < n; j++) {
    const x = (j + 0.5) / PPQ;
    while (ti + 1 < tm.length && x >= tm[ti + 1][0]) ti++;
    while (seg + 1 < ctr.length && x > ctr[seg + 1]) seg++;
    let f;
    if (!ctr.length) f = 1;
    else if (x <= ctr[0]) f = fac[0];
    else if (seg + 1 >= ctr.length) f = fac[fac.length - 1];
    else f = fac[seg] + (fac[seg + 1] - fac[seg]) * clamp((x - ctr[seg]) / (ctr[seg + 1] - ctr[seg]), 0, 1);
    cum[j + 1] = cum[j] + 60 / tm[ti][1] * f / PPQ;
  }
  const T = (b) => {
    const x = Math.max(0, b) * PPQ, j = Math.min(n - 1, Math.floor(x));
    return cum[j] + (cum[j + 1] - cum[j]) * (x - j);
  };
  const rng = lcg(7919 + idx * 131), N = mv.notes, ev = [];
  for (let i = 0; i < N.length; ) {
    let j = i + 1;
    while (j < N.length && N[j][0] - N[i][0] < 4e-3) j++;
    const grp = N.slice(i, j).sort((a, b) => a[2] - b[2]);
    grp.forEach(([t, d, m, vel], k) => {
      const t0 = T(t), roll = grp.length > 2 ? Math.min(0.018, k * 45e-4) : 0;
      ev.push({ b: t, t: Math.max(0, t0 + roll + (rng() - 0.5) * 8e-3), m, v: clamp((vel - 14) / 100 * (0.94 + 0.12 * rng()), 0.04, 1), d: Math.max(0.12, T(t + d) - t0) });
    });
    i = j;
  }
  ev.sort((a, b) => a.t - b.t);
  const len = T(total);
  const keys0 = /* @__PURE__ */ new Set();
  let E = 0;
  for (const e of ev) {
    if (e.t < 30) keys0.add(e.m);
    const amp = 0.05 + 0.95 * Math.pow(e.v, 1.6), tau = clamp(1.7 - 0.02 * (e.m - 60), 0.5, 2.6);
    E += amp * amp * Math.min(tau, e.d + 0.3);
  }
  const P = E / len;
  return { ev, len, T, keys0, P, trim: clamp(Math.pow(10, (LEVEL - (LEVEL_A + LEVEL_B * 10 * Math.log10(P))) / 20), 0.45, 1.5) };
}
var LEVEL = -20.5;
var LEVEL_A = -16.13;
var LEVEL_B = 1.55;
var MASTER = 1;
var MUSIC = 1.2;
var AMB = 0.55;
var G = { drip: 0.36, bubble: 0.36, trickle: 0.36, wash: 0.3, fall: 0.3, gravel: 0.42, stone: 0.45, wood: 0.42, snow: 0.42, asphalt: 0.45, soft: 0.45, leaves: 0.45, crow: 0.14, clap: 0.38, bell: 0.45 };
var AHEAD = 1.5;
var GAP = 3;
var XFADE = 1.6;
var CURVE_IN = new Float32Array(64);
var CURVE_OUT = new Float32Array(64);
for (let i = 0; i < 64; i++) {
  const u = i / 63;
  CURVE_IN[i] = Math.sin(u * Math.PI / 2);
  CURVE_OUT[i] = Math.cos(u * Math.PI / 2);
}
var ROOMS = ["hall", "wood"];
var ROOM_IR = {
  hall: { sec: 3.4, rt: 2.3, pre: 0.02, k0: 0.6, k1: 0.05, tauK: 0.55, build: 0.01, early: 10, spread: 0.08, hp: 90 },
  wood: { sec: 2.2, rt: 1.35, pre: 0.012, k0: 0.4, k1: 0.04, tauK: 0.35, build: 6e-3, early: 16, spread: 0.11, hp: 110 }
};
var SEND = {
  out: { music: [0.42, 0], amb: [0.2, 0], self: [0.16, 0], dry: 1 },
  sanjusangendo: { music: [0, 0.5], amb: [0, 0.22], self: [0, 0.4], dry: 0.9 }
};
var SURF = {
  1: ["asphalt", 1, 1],
  2: ["asphalt", 0.9, 1.04],
  3: ["stone", 0.8, 1.05],
  4: ["stone", 1, 1.1],
  5: ["gravel", 1, 1],
  6: ["soft", 1, 1],
  7: ["soft", 0.65, 1.1],
  8: ["soft", 0.4, 0.95],
  9: ["leaves", 0.9, 1],
  10: ["gravel", 0.75, 0.88],
  11: ["gravel", 1.15, 0.84],
  12: ["stone", 0.85, 0.97],
  13: ["gravel", 0.45, 0.78],
  14: ["gravel", 0.9, 1],
  15: ["soft", 0.9, 0.95],
  16: ["stone", 0.9, 1.08],
  17: ["stone", 1, 0.92],
  18: ["wood", 1, 1],
  255: ["wood", 1.05, 0.95]
};
var NOSNOW = { 1: 1, 2: 1, 18: 1, 255: 1 };
var INTERIORS = { sanjusangendo: 1 };
var SPEED_OF_SOUND = 343;
function createAudio(opts = {}) {
  let ctx = null, started = false, enabled = null, timer = 0, MOV = null;
  let master, comp, lim, clip, music, tone, bodyG, out, outLP1, outLP2, outG, selfBus, fallBus, fallG, fallLP, room = {};
  const KIT = opts.kit || { KEYS: {}, BANK: {}, done: 0, total: 0, sfx: 0, cpu: 0 };
  const KEYS = KIT.KEYS, BANK = KIT.BANK, LASTID = {}, PREP = {};
  let queue = [], allJobs = [], inflight = 0, worker = null, fallbackOn = false, t0Start = 0, tFirst = 0, tKit = 0;
  let cur = null, dying = [], timeline = [], want = { mi: opts.startMovement ?? 0, beat: opts.startBeat || 0, fade: 0 }, lastNow = -1, lastIdx = -1;
  const live = () => !!ctx && (ctx.state === "running" || !!opts.context);
  let mode = "title", interior = null, gnd = 1, muf = 0, interiorK = 0, roomKey = "out", lastSlow = -1;
  let stepPhase = 0.85, foot = 0, fallNext = 0, clock = 0, crowT = 80 + 140 * Math.random(), lastBell = -99;
  const LAST = new Float64Array(64).fill(NaN), bells = /* @__PURE__ */ new Map(), strikes = [];
  const toBuffer = (r) => {
    const b = ctx.createBuffer(r.data.length, r.data[0].length, r.rate);
    r.data.forEach((d, c) => b.getChannelData(c).set(d));
    return b;
  };
  function take(r) {
    if (r.kind) {
      (BANK[r.kind] || (BANK[r.kind] = []))[r.id] = { raw: r, buf: null };
      KIT.sfx++;
    } else KEYS[r.m] = { raw: r, buf: null };
    KIT.done++;
    KIT.cpu += r.ms || 0;
    if (KIT.done >= KIT.total) tKit = performance.now() - t0Start;
  }
  const keyBuf = (k) => {
    const s = KEYS[k];
    if (!s) return null;
    if (!s.buf) {
      s.buf = toBuffer(s.raw);
      s.raw = null;
    }
    return s.buf;
  };
  const bufOf = (kind, id) => {
    const bk = BANK[kind], s = bk && bk[id];
    if (!s) return null;
    if (!s.buf) {
      s.buf = toBuffer(s.raw);
      s.raw = null;
    }
    return s.buf;
  };
  function pick(kind) {
    const bk = BANK[kind];
    if (!bk) return -1;
    let n = 0;
    for (let i = 0; i < bk.length; i++) if (bk[i]) n++;
    if (!n) return -1;
    let id = Math.floor(Math.random() * bk.length), g = 0;
    while (!bk[id] && g++ < 64) id = (id + 1) % bk.length;
    if (id === LASTID[kind] && n > 1) {
      do
        id = (id + 1) % bk.length;
      while (!bk[id]);
    }
    return LASTID[kind] = id;
  }
  const runJob = (K, j) => j.sfx ? K.sfx(j.sfx, j.id) : K.note(j.m, j.need);
  function pump() {
    while (worker && inflight < 2 && queue.length) {
      inflight++;
      worker.postMessage(queue.splice(0, 3));
    }
  }
  function mainThread() {
    fallbackOn = true;
    const K = synthKit();
    queue = allJobs.filter((j) => j.sfx ? !(BANK[j.sfx] && BANK[j.sfx][j.id]) : !KEYS[j.m]);
    const step = () => {
      const t = performance.now();
      while (queue.length && performance.now() - t < 10) {
        const j = queue.shift(), t1 = performance.now(), r = runJob(K, j);
        r.ms = performance.now() - t1;
        take(r);
      }
      if (queue.length) setTimeout(step, 0);
    };
    step();
  }
  function loadKit(jobs) {
    queue = jobs.slice();
    allJobs = jobs.slice();
    KIT.total += jobs.length;
    if (!jobs.length) {
      tKit = 0;
      return;
    }
    try {
      const src = `const K = (${synthKit.toString()})();
self.onmessage = (e) => { const J = e.data; J.forEach((j, i) => { const t = performance.now(), r = j.sfx ? K.sfx(j.sfx, j.id) : K.note(j.m, j.need); r.ms = performance.now() - t; r.last = i === J.length - 1; self.postMessage(r, r.data.map((d) => d.buffer)); }); };`;
      const w = new Worker(URL.createObjectURL(new Blob([src], { type: "text/javascript" })));
      w.onmessage = (e) => {
        take(e.data);
        if (e.data.last) {
          inflight--;
          pump();
        }
        if (KIT.done >= KIT.total) w.terminate();
      };
      w.onerror = (e) => {
        if (e && e.preventDefault) e.preventDefault();
        try {
          w.terminate();
        } catch (x) {
        }
        worker = null;
        inflight = 0;
        mainThread();
      };
      worker = w;
      pump();
    } catch (e) {
      worker = null;
      mainThread();
    }
  }
  function prioritize(keys) {
    const f = [], r = [];
    for (const j of queue) (!j.sfx && keys.has(j.m) ? f : r).push(j);
    if (f.length) queue = f.concat(r);
    pump();
  }
  const ready = (keys) => {
    for (const k of keys) if (!KEYS[k]) return false;
    return true;
  };
  function setup(score) {
    MOV = score.movements;
    if (typeof want.mi === "string") {
      const k = MOV.findIndex((m) => m.id === want.mi);
      want.mi = k < 0 ? 0 : k;
    }
    MOV.forEach((m, i) => {
      m.index = i;
      m.sec = (() => {
        const tm = m.tempo_map && m.tempo_map.length ? m.tempo_map : [[0, m.bpm]];
        let s = 0;
        for (let k = 0; k < tm.length; k++) {
          const b1 = k + 1 < tm.length ? tm[k + 1][0] : m.total_beats;
          s += (b1 - tm[k][0]) * 60 / tm[k][1];
        }
        return s;
      })();
    });
    const need = {}, first = {}, mi0 = clamp(Math.floor(num(want.mi)), 0, MOV.length - 1);
    MOV.forEach((m, mi) => {
      const spb = 60 / Math.min(...(m.tempo_map || [[0, m.bpm]]).map((x) => x[1]));
      for (const [t, d, p] of m.notes) {
        need[p] = Math.max(need[p] || 0, Math.min(d * spb * 1.35 + 1.2, 12));
        if (mi === mi0 && (first[p] === void 0 || t < first[p])) first[p] = t;
      }
    });
    const pitches = Object.keys(need).map(Number), kj = (p) => ({ m: p, need: need[p] });
    const k1 = pitches.filter((p) => first[p] !== void 0).sort((a, b) => first[a] - first[b]).map(kj), k2 = pitches.filter((p) => first[p] === void 0).sort((a, b) => a - b).map(kj);
    const sj = (kinds) => {
      const o = [];
      for (const k of kinds) for (let i = 0; i < COUNTS2[k]; i++) if (!(BANK[k] && BANK[k][i])) o.push({ sfx: k, id: i });
      return o;
    };
    const jobs = [...k1, ...sj(["stone", "gravel", "wood", "snow", "asphalt", "soft", "leaves"]), ...k2, ...sj(["drip", "bubble", "trickle", "bell", "crow", "wash", "fall", "clap"])].filter((j) => j.sfx || !KEYS[j.m]);
    loadKit(jobs);
  }
  const prep = (mi) => PREP[mi] || (PREP[mi] = prepare(MOV[mi], mi));
  function trimPrep(keep) {
    const ks = Object.keys(PREP);
    if (ks.length > 4) {
      for (const k of ks) if (!keep.includes(+k)) delete PREP[k];
    }
  }
  function makeIR(o) {
    const rate = ctx.sampleRate, n = Math.floor(rate * o.sec), b = ctx.createBuffer(2, n, rate), pre = Math.floor(o.pre * rate), hk = 1 - Math.exp(-2 * Math.PI * o.hp / rate);
    for (let c = 0; c < 2; c++) {
      const d = b.getChannelData(c);
      let lp = 0, hz0 = 0;
      for (let i = pre; i < n; i++) {
        const t = (i - pre) / rate, k = o.k1 + (o.k0 - o.k1) * Math.exp(-t / o.tauK);
        lp += (Math.random() * 2 - 1 - lp) * k;
        hz0 += (lp - hz0) * hk;
        d[i] = (lp - hz0) * Math.exp(-6.908 * t / o.rt) * Math.min(1, t / o.build);
      }
      for (let r = 0; r < o.early; r++) d[pre + Math.floor((2e-3 + Math.random() * o.spread) * rate)] += (Math.random() < 0.5 ? -1 : 1) * (0.5 - r / o.early * 0.35);
    }
    return b;
  }
  function soundboard(sec) {
    const rate = ctx.sampleRate, n = Math.floor(rate * sec), b = ctx.createBuffer(2, n, rate);
    for (let c = 0; c < 2; c++) {
      const d = b.getChannelData(c);
      for (let k = 0; k < 260; k++) {
        const f = 70 * Math.pow(60, Math.random()), dec = 18 + f * 0.035, a = (Math.random() * 2 - 1) / Math.sqrt(1 + f / 600), w = 2 * Math.PI * f / rate, ph = Math.random() * 6.28;
        for (let i = 0; i < n; i++) {
          const e = Math.exp(-dec * i / rate);
          if (e < 1e-3) break;
          d[i] += a * e * Math.sin(w * i + ph);
        }
      }
    }
    return b;
  }
  function build() {
    const AC = opts.context ? function() {
      return opts.context;
    } : window.AudioContext || window.webkitAudioContext;
    ctx = new AC({ latencyHint: "playback" });
    const wake = () => {
      if (ctx && enabled && ctx.state !== "running" && !opts.context) {
        try {
          const r = ctx.resume();
          if (r && r.catch) r.catch(() => {
          });
        } catch (e) {
        }
      }
    };
    if (!opts.context && typeof document !== "undefined") {
      document.addEventListener("visibilitychange", wake);
      addEventListener("pointerdown", wake, { passive: true });
      addEventListener("keydown", wake, { passive: true });
    }
    master = ctx.createGain();
    master.gain.value = 0;
    comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -16;
    comp.ratio.value = 2.5;
    comp.attack.value = 0.02;
    comp.release.value = 0.3;
    lim = ctx.createDynamicsCompressor();
    lim.threshold.value = -2;
    lim.knee.value = 0;
    lim.ratio.value = 20;
    lim.attack.value = 2e-3;
    lim.release.value = 0.12;
    clip = ctx.createWaveShaper();
    const cv = new Float32Array(2049);
    for (let i = 0; i < cv.length; i++) {
      const x = i / 1024 - 1, a = Math.abs(x), t = 0.85;
      cv[i] = Math.sign(x) * (a <= t ? a : t + (1 - t) * Math.tanh((a - t) / (1 - t)));
    }
    clip.curve = cv;
    clip.oversample = "2x";
    master.connect(comp);
    comp.connect(lim);
    lim.connect(clip);
    clip.connect(ctx.destination);
    ROOMS.forEach((r, i) => {
      const inG = ctx.createGain(), conv = ctx.createConvolver(), ret = ctx.createGain();
      conv.connect(ret);
      ret.connect(master);
      room[r] = { inG, conv, ret, music: ctx.createGain(), amb: ctx.createGain(), self: ctx.createGain(), on: false, off: 0 };
      for (const k of ["music", "amb", "self"]) {
        room[r][k].gain.value = 0;
        room[r][k].connect(inG);
      }
      if (!opts.noRooms) setTimeout(() => {
        if (ctx) room[r].conv.buffer = makeIR(ROOM_IR[r]);
      }, 30 + i * 70);
    });
    music = ctx.createGain();
    music.gain.value = MUSIC;
    tone = ctx.createBiquadFilter();
    tone.type = "highshelf";
    tone.frequency.value = 3e3;
    tone.gain.value = -2;
    const body = ctx.createConvolver();
    if (!opts.noBody) body.buffer = soundboard(0.09);
    bodyG = ctx.createGain();
    bodyG.gain.value = 0.55;
    music.connect(tone);
    tone.connect(master);
    tone.connect(body);
    body.connect(bodyG);
    bodyG.connect(master);
    for (const r of ROOMS) tone.connect(room[r].music);
    out = ctx.createGain();
    out.gain.value = 1;
    const hp = ctx.createBiquadFilter();
    hp.type = "highpass";
    hp.frequency.value = 40;
    hp.Q.value = 0.7;
    outLP1 = ctx.createBiquadFilter();
    outLP1.type = "lowpass";
    outLP1.frequency.value = 16e3;
    outLP1.Q.value = 0.6;
    outLP2 = ctx.createBiquadFilter();
    outLP2.type = "lowpass";
    outLP2.frequency.value = 16e3;
    outLP2.Q.value = 0.6;
    outG = ctx.createGain();
    outG.gain.value = AMB;
    out.connect(hp);
    hp.connect(outLP1);
    outLP1.connect(outLP2);
    outLP2.connect(outG);
    outG.connect(master);
    for (const r of ROOMS) outG.connect(room[r].amb);
    fallG = ctx.createGain();
    fallG.gain.value = 0;
    fallLP = ctx.createBiquadFilter();
    fallLP.type = "lowpass";
    fallLP.frequency.value = 2500;
    fallLP.Q.value = 0.5;
    fallBus = ctx.createGain();
    fallBus.connect(fallLP);
    fallLP.connect(fallG);
    fallG.connect(out);
    selfBus = ctx.createGain();
    selfBus.gain.value = AMB;
    const shp = ctx.createBiquadFilter();
    shp.type = "highpass";
    shp.frequency.value = 60;
    shp.Q.value = 0.7;
    selfBus.connect(shp);
    shp.connect(master);
    for (const r of ROOMS) shp.connect(room[r].self);
  }
  function setT(p, i, v, tc) {
    if (Math.abs(v - LAST[i]) > 1e-3 * Math.max(1, Math.abs(v)) || !(LAST[i] === LAST[i])) {
      LAST[i] = v;
      p.setTargetAtTime(v, ctx.currentTime, tc);
    }
  }
  function keyFor(m) {
    if (KEYS[m]) return [m, 1];
    for (const d of [-1, 1, -2, 2]) if (KEYS[m + d]) return [m + d, Math.pow(2, -d / 12)];
    return null;
  }
  function strike(e, at, ep) {
    const kf = keyFor(e.m);
    if (!kf) return;
    const buf = keyBuf(kf[0]);
    if (!buf) return;
    const rate = kf[1], len = buf.duration / rate;
    if (len < 0.05) return;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.playbackRate.value = rate;
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.Q.value = 0.5;
    const v2 = e.v * e.v;
    lp.frequency.value = Math.min(15e3, (hz(e.m) * (3 + 10 * v2) + 900 + 5e3 * v2) * ep.tone);
    const g = ctx.createGain(), amp = (0.05 + 0.95 * Math.pow(e.v, 1.6)) * ep.trim;
    g.gain.setValueAtTime(amp, at);
    let last2 = g;
    src.connect(lp);
    lp.connect(g);
    if (ctx.createStereoPanner) {
      const p = ctx.createStereoPanner();
      p.pan.value = clamp((e.m - 62) / 70, -0.4, 0.4);
      g.connect(p);
      last2 = p;
    }
    last2.connect(ep.bus);
    src.start(at);
    let end;
    if (e.d < len) {
      const tau = 0.06 + 0.24 * clamp((72 - e.m) / 48, 0, 1), up = at + e.d;
      g.gain.setValueAtTime(amp, up);
      g.gain.setTargetAtTime(0, up, tau);
      end = up + tau * 7;
      src.stop(end);
    } else {
      end = at + len;
      src.stop(end);
    }
    const old = ep.active[e.m];
    if (old && old.end > at) {
      try {
        old.g.gain.cancelScheduledValues(at);
        old.g.gain.setTargetAtTime(0, at, 0.03);
        old.src.stop(at + 0.25);
      } catch (x) {
      }
    }
    ep.active[e.m] = { src, g, end };
    ep.voices.add(src);
    src.onended = () => {
      ep.voices.delete(src);
      try {
        src.disconnect();
        lp.disconnect();
        g.disconnect();
        if (last2 !== g) last2.disconnect();
      } catch (x) {
      }
    };
  }
  function newEpoch(mi, when, fadeIn, beat) {
    const p = prep(mi), mv = MOV[mi], bus = ctx.createGain(), outg = ctx.createGain();
    if (fadeIn) {
      bus.gain.value = 0;
      bus.gain.setValueCurveAtTime(CURVE_IN, when, fadeIn);
    } else bus.gain.value = 1;
    outg.gain.value = 1;
    bus.connect(outg);
    outg.connect(music);
    const off = beat > 0 ? p.T(beat) : 0;
    let c0 = 0;
    while (c0 < p.ev.length && p.ev[c0].t < off - 1e-3) c0++;
    const ep = { mi, mv, p, bus, outg, t0: when, off, cur: c0, active: {}, voices: /* @__PURE__ */ new Set(), dead: false, until: 0, tone: 0.95, trim: p.trim };
    timeline.push({ mi, t0: when - off, t1: when - off + p.len });
    if (timeline.length > 8) timeline.shift();
    trimPrep([mi, (mi + 1) % MOV.length]);
    return ep;
  }
  function retire(ep, until) {
    ep.until = until;
    dying.push(ep);
  }
  function endEpoch(ep, when, fade) {
    if (ep.dead) return;
    ep.dead = true;
    ep.until = when + fade + 0.4;
    ep.outg.gain.setValueCurveAtTime(CURVE_OUT, when, fade);
    dying.push(ep);
  }
  function tick() {
    if (!live() || !MOV) return;
    const now = ctx.currentTime;
    for (let i = dying.length - 1; i >= 0; i--) {
      const ep = dying[i];
      if (now > ep.until) {
        for (const v of ep.voices) {
          try {
            v.stop();
          } catch (x) {
          }
        }
        try {
          ep.bus.disconnect();
          ep.outg.disconnect();
        } catch (x) {
        }
        dying.splice(i, 1);
      }
    }
    if (!enabled || opts.noMusic) return;
    if (want) {
      const p = prep(want.mi);
      if (ready(p.keys0)) {
        const when = now + (cur ? 0.25 : 0.15);
        if (cur) endEpoch(cur, when, XFADE);
        cur = newEpoch(want.mi, when, cur ? XFADE * 0.5 : 0, want.beat || 0);
        want = null;
        if (!tFirst) tFirst = performance.now() - t0Start;
      } else prioritize(p.keys0);
    }
    const horizon = now + AHEAD;
    for (let guard = 0; cur && guard < 6e3; guard++) {
      const e = cur, ev = e.p.ev[e.cur];
      if (!ev) {
        const ni = (e.mi + 1) % MOV.length, np = prep(ni);
        if (!ready(np.keys0)) {
          prioritize(np.keys0);
          break;
        }
        const endT = e.t0 - e.off + e.p.len + GAP;
        retire(e, endT + 8);
        cur = newEpoch(ni, endT, 0, 0);
        continue;
      }
      const at = e.t0 + ev.t - e.off;
      if (at > horizon) break;
      e.cur++;
      if (at < now - 0.03) continue;
      strike(ev, Math.max(at, now + 4e-3), e);
    }
  }
  function heard(now) {
    let r = null;
    for (const t of timeline) if (t.t0 - 2.5 <= now) r = t;
    return r ? MOV[r.mi] : null;
  }
  function grain(kind, dest, at, gain, rate, pan, id, fc) {
    if (id === void 0 || id === null) id = pick(kind);
    if (id < 0) return false;
    const b = bufOf(kind, id);
    if (!b) return false;
    const src = ctx.createBufferSource();
    src.buffer = b;
    src.playbackRate.value = rate;
    const g = ctx.createGain();
    g.gain.value = gain;
    let lp = null;
    if (fc) {
      lp = ctx.createBiquadFilter();
      lp.type = "lowpass";
      lp.frequency.value = fc;
      lp.Q.value = 0.5;
      src.connect(lp);
      lp.connect(g);
    } else src.connect(g);
    let last2 = g;
    if (pan && ctx.createStereoPanner) {
      const p = ctx.createStereoPanner();
      p.pan.value = clamp(pan, -1, 1);
      g.connect(p);
      last2 = p;
    }
    last2.connect(dest);
    src.start(at);
    src.onended = () => {
      try {
        src.disconnect();
        if (lp) lp.disconnect();
        g.disconnect();
        if (last2 !== g) last2.disconnect();
      } catch (x) {
      }
    };
    return true;
  }
  const logn = (s) => Math.exp(s * (Math.random() + Math.random() + Math.random() - 1.5) * 0.8);
  const sgn = () => Math.random() < 0.5 ? -1 : 1;
  function bellStrike(o = {}) {
    const dist = clamp(num(o.dist, 300), 5, 3e3), az = num(o.az, 0), idn = idNum(o.id), id = idn % 3;
    const b = bufOf("bell", id);
    if (!b) return false;
    const at = (ctx.currentTime || 0) + 0.03 + (o.delay === false ? 0 : dist / SPEED_OF_SOUND) + num(o.later);
    const src = ctx.createBufferSource();
    src.buffer = b;
    src.playbackRate.value = 1 + 4e-3 * (idn * 7 % 5 - 2);
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.Q.value = 0.5;
    lp.frequency.value = clamp(15e3 * Math.exp(-dist / 330), 900, 15e3) * (0.78 + 0.22 * Math.cos(az));
    const g = ctx.createGain();
    g.gain.value = (o.gain ?? 1) * G.bell * Math.pow(clamp(70 / (dist + 30), 0.05, 1.2), 0.6);
    src.connect(lp);
    lp.connect(g);
    let last2 = g;
    if (ctx.createStereoPanner) {
      const p = ctx.createStereoPanner();
      p.pan.value = clamp(Math.sin(az) * 0.85, -1, 1);
      g.connect(p);
      last2 = p;
    }
    last2.connect(out);
    src.start(at);
    if (opts.debug) strikes.push({ at: +at.toFixed(2), dist, id, az, gain: g.gain.value });
    src.onended = () => {
      try {
        src.disconnect();
        lp.disconnect();
        g.disconnect();
        if (last2 !== g) last2.disconnect();
      } catch (x) {
      }
    };
    return at;
  }
  function bellsUpdate(list, k) {
    if (!Array.isArray(list)) return;
    const sorted = list.filter((b) => b && typeof b === "object").slice().sort((a, b) => num(a.dist, 1e9) - num(b.dist, 1e9));
    sorted.forEach((b, rank) => {
      const id = b.id ?? rank;
      let st = bells.get(id);
      if (!st) {
        st = { next: clock + 6 + 40 * Math.random(), n: 0, seen: clock };
        bells.set(id, st);
      }
      st.seen = clock;
      if (clock < st.next) return;
      if (clock - lastBell < 14) {
        st.next = clock + 6 + 10 * Math.random();
        return;
      }
      lastBell = clock;
      const dist = num(b.dist, 300), strikes2 = Math.random() < 0.22 ? 2 + (Math.random() < 0.4 ? 1 : 0) : 1;
      let later = 0;
      for (let i = 0; i < strikes2; i++) {
        bellStrike({ dist, az: b.az, id, gain: (1 - 0.1 * i) * k, later });
        later += 20 + 8 * Math.random();
      }
      st.next = clock + (70 + 80 * Math.random()) * (1 + 0.6 * rank) * (1 + dist / 2400) + later;
    });
    if (bells.size > 16) {
      for (const [id, st] of bells) if (clock - st.seen > 300) bells.delete(id);
    }
  }
  function update(dt, s) {
    if (!ctx || !started || !MOV || !s) return;
    dt = clamp(num(dt, 0.016), 0, 0.25);
    clock += dt;
    const now = ctx.currentTime;
    mode = s.mode === "walk" || s.mode === "fly" || s.mode === "title" ? s.mode : "walk";
    interior = typeof s.interior === "string" && INTERIORS[s.interior] ? s.interior : null;
    const camZ = num(s.camZ, 2), walk = clamp(num(s.walkSpeed), 0, 8), season = s.season === 1 ? 1 : 0, surf = num(s.surf, 0);
    const water = clamp(num(s.water), 0, 1), fall = clamp(num(s.fall), 0, 1), weir = s.weir === void 0 ? clamp((water - 0.55) / 0.45, 0, 1) * 0.7 : clamp(num(s.weir), 0, 1);
    gnd = 1 - sstep(30, 100, camZ);
    if (!live() || !enabled) return;
    if (now - lastSlow > 0.1) {
      lastSlow = now;
      const rk = interior || "out", M = SEND[rk];
      roomKey = rk;
      muf += ((interior ? 1 : 0) - muf) * (1 - Math.exp(-0.1 / 0.6));
      interiorK = muf;
      const f = 600 * Math.pow(16e3 / 600, 1 - muf);
      setT(outLP1.frequency, 0, f, 0.06);
      setT(outLP2.frequency, 1, f, 0.06);
      setT(outG.gain, 2, AMB * lerp(1, 0.32, muf), 0.12);
      for (let i = 0; i < ROOMS.length; i++) {
        const R = room[ROOMS[i]], wantRoom = M.music[i] + M.amb[i] + M.self[i] > 0;
        if (wantRoom) {
          R.off = 0;
          if (!R.on) {
            R.inG.connect(R.conv);
            R.on = true;
          }
        } else if (R.on) {
          if (!R.off) R.off = now;
          else if (now - R.off > 4.5) {
            try {
              R.inG.disconnect(R.conv);
            } catch (e) {
            }
            R.on = false;
            R.off = 0;
          }
        }
        setT(R.music.gain, 3 + i, M.music[i], 0.7);
        setT(R.amb.gain, 8 + i, M.amb[i], 0.7);
        setT(R.self.gain, 13 + i, M.self[i], 0.7);
      }
      setT(tone.gain, 18, -2 - 3 * interiorK, 0.8);
      setT(music.gain, 19, MUSIC * M.dry, 0.8);
    }
    tick();
    if (opts.onMovement) {
      const h = heard(now);
      if (h && h.index !== lastIdx) {
        lastIdx = h.index;
        try {
          opts.onMovement({ index: h.index, id: h.id, title: h.title, title_ja: h.title_ja });
        } catch (e) {
        }
      }
    }
    if (opts.noAmb) return;
    const gn = gnd, titleK = mode === "title" ? 0.55 : 1;
    const w = water * gn * titleK;
    if (w > 0.02) {
      if (Math.random() < (0.2 + 0.9 * w) * dt) grain("trickle", out, now + 0.02, G.trickle * 0.8 * w * logn(0.45), 0.9 + 0.25 * Math.random(), sgn() * (0.2 + 0.55 * Math.random()));
      if (Math.random() < (0.15 + 0.75 * w) * dt) grain("drip", out, now + 0.02, G.drip * 0.8 * w * logn(0.5), 0.8 + 0.5 * Math.random(), sgn() * Math.random() * 0.7);
      if (Math.random() < (0.05 + 0.3 * w) * dt) grain("bubble", out, now + 0.02, G.bubble * 0.7 * w * logn(0.5), 0.85 + 0.4 * Math.random(), sgn() * Math.random() * 0.7);
    }
    const wk = weir * gn * titleK;
    if (wk > 0.05 && Math.random() < (0.12 + 0.3 * wk) * dt) grain("wash", out, now + 0.02, G.wash * wk * logn(0.35), 0.92 + 0.16 * Math.random(), 0);
    const fk = fall * gn * titleK;
    if (fk > 0.02) {
      if (fallNext < now) fallNext = now + 0.03;
      while (fallNext < now + 0.7) {
        grain("fall", fallBus, fallNext, 1, 0.98 + 0.04 * Math.random(), 0);
        fallNext += 2.7;
      }
    } else if (fallNext > 0 && fallNext < now) fallNext = 0;
    setT(fallG.gain, 20, G.fall * Math.pow(fk, 1.2), 0.25);
    setT(fallLP.frequency, 21, 1800 + 8500 * fk, 0.25);
    if (mode === "walk" && walk > 0.12 && gn > 0.2) {
      const sps = walk < 1.7 ? walk / 0.77 : 2.2 + (walk - 1.7) * 0.5;
      stepPhase += sps * dt;
      for (let n = 0; stepPhase >= 1 && n < 2; n++) {
        stepPhase -= 1;
        foot ^= 1;
        let sf = interior ? SURF[255] : SURF[surf] || ["stone", 0.7, 1];
        if (season === 1 && !interior && !NOSNOW[surf]) sf = ["snow", 0.9, 1];
        const run = walk > 2.6, gw = (0.8 + 0.2 * Math.min(1, walk / 1.6)) * (run ? 1.3 : 1);
        grain(sf[0], selfBus, now + 0.01, G[sf[0]] * sf[1] * gw * logn(0.3), (foot ? 0.97 : 1.03) * (0.97 + 0.06 * Math.random()) * sf[2] * (run ? 1.08 : 1), (foot ? 1 : -1) * 0.09);
      }
      if (stepPhase > 1) stepPhase = 0;
    } else stepPhase = Math.max(stepPhase, 0.85);
    crowT -= dt;
    if (crowT <= 0) {
      crowT = 150 + 250 * Math.random();
      if (!interior && gn > 0.2 && mode !== "title") grain("crow", out, now + 0.05, G.crow * gn * logn(0.3), 0.92 + 0.16 * Math.random(), sgn() * (0.3 + 0.5 * Math.random()), null, 2800);
    }
    bellsUpdate(s.bells, lerp(0.55, 1, gn));
  }
  function hold(p, t) {
    if (p.cancelAndHoldAtTime) p.cancelAndHoldAtTime(t);
    else {
      const v = p.value;
      p.cancelScheduledValues(t);
      p.setValueAtTime(v, t);
    }
  }
  function applyEnabled() {
    if (!ctx) return;
    const now = ctx.currentTime;
    if (opts.context) {
      master.gain.value = enabled ? MASTER : 0;
      return;
    }
    if (enabled) {
      try {
        if (ctx.state === "suspended") {
          const r = ctx.resume();
          if (r && r.catch) r.catch(() => {
          });
        }
      } catch (e) {
      }
      hold(master.gain, now);
      master.gain.setTargetAtTime(MASTER, now, 0.5);
    } else {
      hold(master.gain, now);
      master.gain.setTargetAtTime(0, now, 0.2);
      setTimeout(() => {
        if (!enabled && ctx && ctx.suspend) {
          try {
            ctx.suspend();
          } catch (e) {
          }
        }
      }, 1400);
    }
  }
  async function start() {
    if (started) {
      if (enabled) applyEnabled();
      return;
    }
    started = true;
    if (enabled === null) enabled = true;
    try {
      build();
    } catch (e) {
      console.warn("audio unavailable", e);
      ctx = null;
      started = false;
      return;
    }
    t0Start = performance.now();
    try {
      if (!opts.context) await Promise.race([ctx.resume(), new Promise((r) => setTimeout(r, 400))]);
    } catch (e) {
    }
    applyEnabled();
    await new Promise((r) => setTimeout(r, 0));
    if (!ctx) return;
    try {
      const score = opts.score || await (await fetch(opts.scoreUrl || "data/goldberg.json")).json();
      setup(score);
    } catch (e) {
      console.warn("audio: the score failed", e);
      return;
    }
    if (!opts.context) timer = setInterval(tick, 80);
  }
  function setEnabled(on) {
    enabled = !!on;
    if (started && ctx) applyEnabled();
    else if (on && !started) start();
  }
  function jump(i, o = {}) {
    if (!MOV) {
      want = { mi: typeof i === "string" ? i : num(i), beat: num(o.beat), fade: 0 };
      return false;
    }
    const mi = typeof i === "string" ? MOV.findIndex((m) => m.id === i) : clamp(Math.floor(num(i)), 0, MOV.length - 1);
    if (mi < 0) return false;
    want = { mi, beat: num(o.beat), fade: XFADE };
    return true;
  }
  const curIndex = () => {
    const h = ctx && heard(ctx.currentTime);
    return h ? h.index : cur ? cur.mi : want ? want.mi : 0;
  };
  const COUNTS2 = synthKit().COUNTS;
  const api = {
    start,
    setEnabled,
    update,
    jump,
    next: () => jump((curIndex() + 1) % (MOV ? MOV.length : 32)),
    prev: () => jump((curIndex() + (MOV ? MOV.length : 32) - 1) % (MOV ? MOV.length : 32)),
    movements: () => (MOV || []).map((m) => ({ index: m.index, id: m.id, title: m.title, title_ja: m.title_ja, sec: +m.sec.toFixed(1) })),
    nowPlaying: () => {
      const h = ctx && MOV ? heard(ctx.currentTime) : null;
      return h ? { index: h.index, id: h.id, title: h.title, title_ja: h.title_ja } : { index: -1, id: "", title: "", title_ja: "" };
    },
    play: (kind, o = {}) => {
      if (!ctx || !COUNTS2[kind]) return false;
      if (kind === "bell") return !!bellStrike(Object.assign({ delay: false }, o));
      return grain(kind, o.self ? selfBus : out, o.at ?? ctx.currentTime + 0.02, (o.gain ?? 1) * G[kind], o.rate ?? 1, o.pan ?? 0, o.id);
    },
    bell: (o = {}) => !!ctx && !!bellStrike(o),
    whenReady: () => new Promise((res) => {
      const chk = () => {
        if (MOV && KIT.done >= KIT.total) res(KIT);
        else setTimeout(chk, 40);
      };
      chk();
    }),
    kit: KIT,
    /* for debugging: what is playing and how far the kit has got */
    info: () => ({
      started,
      enabled,
      state: ctx && ctx.state,
      movement: cur && cur.mv.id,
      index: cur && cur.mi,
      want: want && want.mi,
      room: roomKey,
      kit: KIT.done + "/" + KIT.total,
      sfx: KIT.sfx,
      worker: fallbackOn ? "main thread" : worker ? "worker" : "done",
      kitMs: tKit ? Math.round(tKit) : null,
      firstNoteMs: tFirst ? Math.round(tFirst) : null,
      cpuMs: Math.round(KIT.cpu),
      gnd: +gnd.toFixed(2),
      muffle: +muf.toFixed(2)
    })
  };
  if (opts.debug) api._dbg = { get ctx() {
    return ctx;
  }, get comp() {
    return comp;
  }, get lim() {
    return lim;
  }, get master() {
    return master;
  }, get out() {
    return out;
  }, tick, prep, get cur() {
    return cur;
  }, get MOV() {
    return MOV;
  }, KIT, KEYS, BANK, strike, bellStrike, timeline, G, SURF, strikes, bells };
  return api;
}
async function renderOffline(o = {}) {
  const rate = o.rate || 48e3, sec = o.sec || 20, step = o.step || 0.25, oac = new OfflineAudioContext(2, Math.ceil(sec * rate), rate);
  const A2 = createAudio({ context: oac, debug: true, score: o.score, kit: o.kit, noMusic: o.music === false, noAmb: o.amb === false, startMovement: o.movement ?? 0, startBeat: o.beat || 0, noRooms: o.rooms === false, scoreUrl: o.scoreUrl });
  await A2.start();
  await A2.whenReady();
  await sleep(o.settle ?? 600);
  for (let i = 0; i * step < sec; i++) {
    const t = i * step;
    oac.suspend(t).then(() => {
      A2.update(step, typeof o.state === "function" ? o.state(t) : o.state || { mode: "walk" });
      if (o.onFrame) o.onFrame(A2, t);
      oac.resume();
    });
  }
  const buffer = await oac.startRendering();
  return { buffer, A: A2 };
}
function wavBytes(buf) {
  const n = buf.length, nc = buf.numberOfChannels, ch = [];
  for (let c = 0; c < nc; c++) ch.push(buf.getChannelData(c));
  const dv = new DataView(new ArrayBuffer(44 + n * nc * 2)), str = (p, s) => {
    for (let i = 0; i < s.length; i++) dv.setUint8(p + i, s.charCodeAt(i));
  };
  str(0, "RIFF");
  dv.setUint32(4, 36 + n * nc * 2, true);
  str(8, "WAVEfmt ");
  dv.setUint32(16, 16, true);
  dv.setUint16(20, 1, true);
  dv.setUint16(22, nc, true);
  dv.setUint32(24, buf.sampleRate, true);
  dv.setUint32(28, buf.sampleRate * nc * 2, true);
  dv.setUint16(32, nc * 2, true);
  dv.setUint16(34, 16, true);
  str(36, "data");
  dv.setUint32(40, n * nc * 2, true);
  for (let i = 0, p = 44; i < n; i++) for (let c = 0; c < nc; c++, p += 2) dv.setInt16(p, clamp(Math.round(ch[c][i] * 32767), -32768, 32767), true);
  return new Uint8Array(dv.buffer);
}

// web/audiotest.js
var COUNTS = synthKit().COUNTS;
var $ = (id) => document.getElementById(id);
var SURF2 = { 0: "none", 1: "asphalt", 2: "asphalt lane", 3: "sidewalk", 4: "stone sett", 5: "gravel", 6: "soil", 7: "grass", 8: "moss", 9: "forest", 10: "riverbed", 11: "ballast", 12: "concrete", 13: "sand", 14: "graves", 15: "farm", 16: "tactile", 17: "stone slab", 18: "wood deck", 255: "wooden floor" };
var logEl = $("log");
var log = (...a) => {
  const s = a.map((x) => typeof x === "string" ? x : JSON.stringify(x)).join(" ");
  console.log(s);
  if (logEl) {
    logEl.textContent += s + "\n";
    logEl.scrollTop = logEl.scrollHeight;
  }
};
window.addEventListener("error", (e) => log("ERROR", e.message, e.filename + ":" + e.lineno));
window.addEventListener("unhandledrejection", (e) => log("REJECTED", String(e.reason && e.reason.stack || e.reason)));
var A = createAudio({ debug: true, onMovement: (m) => {
  $("now").textContent = `${m.title_ja}  \u2014  ${m.title}`;
  log("now playing:", m.index, m.id, m.title);
} });
var W = { mode: "walk", walkSpeed: 0, surf: 5, season: 0, water: 0, fall: 0, weir: 0, camZ: 2, interior: null, bells: [] };
for (const [id, name] of Object.entries(SURF2)) {
  const o = document.createElement("option");
  o.value = id;
  o.textContent = `${id} ${name}`;
  if (+id === 5) o.selected = true;
  $("surf").appendChild(o);
}
for (const kind of Object.keys(COUNTS)) {
  const b = document.createElement("button");
  b.textContent = kind + (COUNTS[kind] > 1 ? ` \xD7${COUNTS[kind]}` : "");
  b.onclick = async () => {
    await begin();
    if (kind === "bell") A.bell({ dist: +$("bdist").value, az: +$("baz").value, id: Math.floor(Math.random() * 3), delay: $("belldelay").checked });
    else A.play(kind, { self: ["gravel", "stone", "wood", "snow", "asphalt", "soft", "leaves"].includes(kind) });
  };
  $("grains").appendChild(b);
}
var began = false;
async function begin() {
  if (began) return;
  began = true;
  await A.start();
}
$("start").onclick = async () => {
  await begin();
  log("started", A.info());
  fillMovements();
};
$("mute").onclick = () => {
  const on = $("mute").classList.toggle("on");
  A.setEnabled(!on);
  $("mute").textContent = on ? "Unmute" : "Mute";
};
$("next").onclick = () => A.next();
$("prev").onclick = () => A.prev();
$("jump").onclick = async () => {
  await begin();
  A.jump(+$("mv").value, { beat: +$("beat").value || 0 });
};
function fillMovements() {
  const ms = A.movements();
  if (!ms.length) {
    setTimeout(fillMovements, 200);
    return;
  }
  if ($("mv").options.length) return;
  for (const m of ms) {
    const o = document.createElement("option");
    o.value = m.index;
    o.textContent = `${m.index}  ${m.title_ja}  (${Math.floor(m.sec / 60)}:${String(Math.round(m.sec % 60)).padStart(2, "0")})`;
    $("mv").appendChild(o);
  }
}
var bind = (id, fn) => {
  const el = $(id), f = () => fn(el);
  el.addEventListener("input", f);
  el.addEventListener("change", f);
  f();
};
bind("mode", (e) => W.mode = e.value);
bind("speed", (e) => {
  W.walkSpeed = +e.value;
  $("speedv").textContent = e.value;
});
bind("surf", (e) => W.surf = +e.value);
bind("season", (e) => W.season = +e.value);
bind("interior", (e) => W.interior = e.value || null);
bind("water", (e) => W.water = +e.value);
bind("weir", (e) => W.weir = +e.value);
bind("fall", (e) => W.fall = +e.value);
bind("camz", (e) => {
  W.camZ = +e.value;
  $("camzv").textContent = e.value;
});
var bellList = () => {
  W.bells = $("bellson").checked ? [{ id: 11, dist: +$("bdist").value, az: +$("baz").value }, { id: 12, dist: 650, az: -2 }] : [];
  $("bdistv").textContent = $("bdist").value;
};
bind("bellson", bellList);
bind("bdist", bellList);
bind("baz", bellList);
$("bellnow").onclick = async () => {
  await begin();
  A.bell({ dist: +$("bdist").value, az: +$("baz").value, id: Math.floor(Math.random() * 3), delay: $("belldelay").checked });
};
var last = performance.now();
var nextInfo = 0;
function frame(t) {
  const dt = (t - last) / 1e3;
  last = t;
  if (began) {
    A.update(dt, W);
    if (t > nextInfo) {
      nextInfo = t + 500;
      $("info").textContent = JSON.stringify(A.info());
    }
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
var db = (x) => +(20 * Math.log10(Math.max(x, 1e-9))).toFixed(1);
function stats(buf, t0 = 0, t1 = buf.duration) {
  let pk = 0, e = 0, n = 0;
  for (let c = 0; c < buf.numberOfChannels; c++) {
    const d = buf.getChannelData(c), i0 = Math.floor(t0 * buf.sampleRate), i1 = Math.min(d.length, Math.floor(t1 * buf.sampleRate));
    for (let i = i0; i < i1; i++) {
      const x = d[i];
      if (Math.abs(x) > pk) pk = Math.abs(x);
      e += x * x;
      n++;
    }
  }
  return { peak: db(pk), rms: db(Math.sqrt(e / Math.max(1, n))) };
}
async function save(name, buf) {
  try {
    const r = await fetch("/__save/" + name, { method: "POST", body: wavBytes(buf) });
    return r.ok;
  } catch (e) {
    return false;
  }
}
var STEP_KINDS = ["gravel", "stone", "wood", "snow", "asphalt", "soft", "leaves"];
var AT = window.AT = { A, createAudio, renderOffline, wavBytes, stats, COUNTS };
AT.runAll = async function(only) {
  const R = { kit: null, aria: null, pitch: null, grains: {}, walk: {}, water: {}, bells: {}, movements: [] };
  const want = (k) => !only || only.includes(k);
  let kit = null;
  const out = (txt) => {
    $("testst").textContent = txt;
    log(txt);
  };
  out("aria \u2026");
  const t0 = performance.now();
  const a = await renderOffline({ movement: "aria", sec: 24, amb: false });
  kit = a.A.kit;
  R.kit = Object.assign({ wallMs: Math.round(performance.now() - t0) }, a.A.info());
  const cur = a.A._dbg.cur;
  R.aria = {
    saved: await save("aria-4bars.wav", a.buffer),
    t0: cur.t0,
    bpm: cur.mv.bpm,
    trim: cur.trim,
    P: cur.p.P,
    len: cur.p.len,
    stats: stats(a.buffer),
    events: cur.p.ev.filter((e) => e.t < 20).map((e) => [+(cur.t0 + e.t).toFixed(4), e.m, +e.v.toFixed(3), +e.d.toFixed(3), +e.b.toFixed(3)]),
    bars: [0, 1, 2, 3, 4].map((i) => stats(a.buffer, 0.15 + i * 4.5, Math.min(24, 0.15 + (i + 1) * 4.5)))
  };
  if (want("pitch")) {
    out("pitch \u2026");
    const ps = [31, 33, 36, 41, 45, 48, 52, 55, 60, 64, 67, 69, 72, 76, 79, 84, 86];
    const score = { movements: [{ id: "pitchtest", title: "pitch test", title_ja: "pitch", meter: [4, 4], bpm: 60, total_beats: ps.length * 2 + 2, bar_beats: [0, 4, 8, 12, 16, 20, 24, 28, 32], notes: ps.map((m, i) => [i * 2, 1.6, m, 70]) }] };
    let pev = null;
    const p = await renderOffline({ score, sec: ps.length * 2 + 3, amb: false, rooms: false, kit, onFrame: (A2, t) => {
      if (t === 1) {
        const c = A2._dbg.cur;
        pev = c.p.ev.map((e) => [+(c.t0 + e.t).toFixed(4), e.m]);
      }
    } });
    R.pitch = { saved: await save("pitch.wav", p.buffer), stats: stats(p.buffer), events: pev };
  }
  if (want("grains")) for (const kind of Object.keys(COUNTS)) {
    out("grain " + kind + " \u2026");
    const long = kind === "bell" ? 44 : kind === "fall" ? 4 : 1.6, n = kind === "bell" ? 1 : 3, sec = n * long + 0.5;
    const g = await renderOffline({ sec, music: false, kit, settle: 150, onFrame: (A2, t) => {
      if (t === 0) for (let i = 0; i < n; i++) A2.play(kind, { id: i, at: 0.1 + i * long, self: STEP_KINDS.includes(kind) });
    } });
    R.grains[kind] = { saved: await save("grain-" + kind + ".wav", g.buffer), stats: stats(g.buffer, 0, sec), peaks: [...Array(n).keys()].map((i) => stats(g.buffer, 0.1 + i * long, 0.1 + (i + 1) * long)) };
  }
  if (want("walk")) {
    const surfs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 255, 0];
    const cases = surfs.map((s) => ["walk-" + s, { surf: s, season: 0 }]).concat([["walk-snow-5", { surf: 5, season: 1 }], ["walk-snow-9", { surf: 9, season: 1 }], ["walk-snow-1", { surf: 1, season: 1 }], ["walk-snow-18", { surf: 18, season: 1 }], ["walk-hall", { surf: 255, season: 0, interior: "sanjusangendo" }], ["run-5", { surf: 5, season: 0, speed: 3.6 }]]);
    for (const [name, c] of cases) {
      out(name + " \u2026");
      const g = await renderOffline({ sec: 6, music: false, kit, settle: 150, step: 1 / 60, state: { mode: "walk", walkSpeed: c.speed || 1.4, surf: c.surf, season: c.season, interior: c.interior || null, camZ: 2 } });
      R.walk[name] = { saved: ["walk-1", "walk-4", "walk-5", "walk-6", "walk-9", "walk-17", "walk-18", "walk-255", "walk-snow-5", "walk-snow-1", "walk-hall", "run-5"].includes(name) ? await save(name + ".wav", g.buffer) : false, stats: stats(g.buffer, 0.2, 6) };
    }
  }
  if (want("water")) {
    for (const [name, st, sec] of [["stream", { water: 1 }, 14], ["weir", { weir: 1 }, 12], ["fall-1", { fall: 1 }, 12], ["fall-0.35", { fall: 0.35 }, 10], ["fall-hall", { fall: 1, interior: "sanjusangendo" }, 8]]) {
      out(name + " \u2026");
      const g2 = await renderOffline({ sec, music: false, kit, settle: 150, step: 0.1, state: Object.assign({ mode: "walk", walkSpeed: 0, camZ: 2 }, st) });
      R.water[name] = { saved: await save("water-" + name + ".wav", g2.buffer), stats: stats(g2.buffer, 1, sec) };
    }
    out("fall + piano \u2026");
    const g = await renderOffline({ sec: 20, kit, settle: 150, state: { mode: "walk", walkSpeed: 0, camZ: 2, fall: 1, water: 1 } });
    R.water.piano_fall = { saved: await save("water-piano-fall.wav", g.buffer), stats: stats(g.buffer, 2, 20) };
  }
  if (want("bells")) {
    for (const [name, dist, id] of [["near", 60, 0], ["mid", 300, 1], ["far", 800, 2]]) {
      out("bell " + name + " \u2026");
      const g2 = await renderOffline({ sec: 46, music: false, kit, settle: 150, onFrame: (A2, t) => {
        if (t === 0) A2.bell({ dist, az: 0.8, id, delay: false });
      } });
      R.bells[name] = { saved: await save("bell-" + name + ".wav", g2.buffer), stats: stats(g2.buffer, 0, 46) };
    }
    out("bell scheduler \u2026");
    const g = await renderOffline({ sec: 420, music: false, kit, settle: 150, step: 0.5, state: { mode: "walk", walkSpeed: 0, camZ: 2, bells: [{ id: 3, dist: 200, az: 0.3 }, { id: 4, dist: 520, az: -1.9 }, { id: 5, dist: 780, az: 2.5 }] }, onFrame: (A2, t) => {
      if (t >= 419) R.bells.log = A2._dbg.strikes.slice();
    } });
    R.bells.scheduler = { stats: stats(g.buffer) };
  }
  if (want("transition")) {
    out("transition \u2026");
    const names = [];
    let tl = null;
    const g = await renderOffline({ movement: "aria", beat: 186, sec: 30, amb: false, kit, onFrame: (A2, t) => {
      const np = A2.nowPlaying();
      if (!names.length || names[names.length - 1][1] !== np.id) names.push([t, np.id]);
      if (t === 29) tl = A2._dbg.timeline.slice();
    } });
    const win = [];
    for (let i = 0; i < 30 * 4; i++) win.push(stats(g.buffer, i * 0.25, (i + 1) * 0.25).rms);
    R.transition = { saved: await save("transition.wav", g.buffer), nowPlaying: names, timeline: tl, rmsPerQuarterSecond: win };
    out("da capo wraps to the Aria \u2026");
    const nm2 = [];
    const w2 = await renderOffline({ movement: "aria_da_capo", beat: 186, sec: 22, amb: false, kit, onFrame: (A2, t) => {
      const np = A2.nowPlaying();
      if (!nm2.length || nm2[nm2.length - 1][1] !== np.id) nm2.push([t, np.id]);
    } });
    R.wrap = { nowPlaying: nm2, stats: stats(w2.buffer) };
    out("hall \u2026");
    const h = await renderOffline({ movement: "aria", sec: 20, amb: false, kit, state: { mode: "walk", interior: "sanjusangendo" } });
    R.hall = { saved: await save("aria-hall.wav", h.buffer), stats: stats(h.buffer, 1, 20) };
    const o2 = await renderOffline({ movement: "aria", sec: 20, amb: false, kit });
    R.hall.outdoors = stats(o2.buffer, 1, 20);
  }
  if (want("movements")) {
    const ms = a.A.movements();
    for (const m of ms) {
      out("movement " + m.id + " \u2026");
      const mv = a.A._dbg.MOV[m.index], bars = mv.bar_beats, beat = bars[Math.floor(bars.length * 0.4)] || 0;
      const g = await renderOffline({ movement: m.index, beat, sec: 18, amb: false, kit, settle: 250 });
      const p = g.A._dbg.prep(m.index);
      R.movements.push({ id: m.id, bpm: mv.bpm, beat, trim: +p.trim.toFixed(3), P: +p.P.toFixed(3), stats: stats(g.buffer, 1, 18), saved: ["var28", "var25", "var22", "var05"].includes(m.id) ? await save("mv-" + m.id + ".wav", g.buffer) : false });
    }
  }
  out("done");
  return R;
};
AT.live = async (secs = 16) => {
  const L = createAudio({ debug: true }), sleep2 = (ms) => new Promise((r) => setTimeout(r, ms));
  const st = { mode: "walk", walkSpeed: 1.4, surf: 5, season: 0, water: 0.6, fall: 0.3, camZ: 2, bells: [{ id: 1, dist: 250, az: 0.5 }] };
  const t0 = performance.now();
  await L.start();
  const tStart = performance.now() - t0;
  let lastT = performance.now(), maxGap = 0, frames = 0;
  const iv = setInterval(() => {
    const n2 = performance.now();
    maxGap = Math.max(maxGap, n2 - lastT);
    lastT = n2;
    frames++;
    L.update(0.016, st);
  }, 16);
  const log2 = [];
  for (let i = 0; i < secs * 2; i++) {
    await sleep2(500);
    if (i === 20) L.jump("var25");
    if (i === 24) L.next();
    if (i % 4 === 3) log2.push({ t: (i + 1) / 2, ctx: +L._dbg.ctx.currentTime.toFixed(2), state: L._dbg.ctx.state, info: L.info(), now: L.nowPlaying().id });
  }
  clearInterval(iv);
  const ctx = L._dbg.ctx, n = L._dbg.cur;
  return { startCallMs: Math.round(tStart), sampleRate: ctx.sampleRate, baseLatency: ctx.baseLatency, state: ctx.state, ctxTime: ctx.currentTime, wall: (performance.now() - t0) / 1e3, maxGapMs: Math.round(maxGap), frames, log: log2, timeline: L._dbg.timeline };
};
AT.ui = async () => {
  const sleep2 = (ms) => new Promise((r) => setTimeout(r, ms)), o = {};
  $("start").click();
  await sleep2(2500);
  o.movements = $("mv").options.length;
  o.now1 = $("now").textContent;
  o.info = $("info").textContent;
  $("mv").value = "5";
  $("jump").click();
  await sleep2(2e3);
  o.now2 = $("now").textContent;
  for (const b of document.querySelectorAll("#grains button")) b.click();
  $("speed").value = "1.5";
  $("speed").dispatchEvent(new Event("input"));
  $("surf").value = "17";
  $("surf").dispatchEvent(new Event("change"));
  $("season").value = "1";
  $("season").dispatchEvent(new Event("change"));
  $("fall").value = "0.8";
  $("fall").dispatchEvent(new Event("input"));
  $("bellson").checked = true;
  $("bellson").dispatchEvent(new Event("change"));
  $("interior").value = "sanjusangendo";
  $("interior").dispatchEvent(new Event("change"));
  $("mute").click();
  await sleep2(500);
  o.muted = A.info().enabled;
  $("mute").click();
  await sleep2(1500);
  o.world = JSON.stringify(W);
  o.after = A.info();
  o.log = $("log").textContent.split("\n").slice(-6);
  return o;
};
log("audiotest ready");
