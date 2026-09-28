// Seeded randomness. Nothing in the book calls Math.random, so every render is identical.
export function hashStr(s) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}

export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// A small random toolkit around one stream.
export class Rng {
  constructor(seed) {
    this.seed = typeof seed === 'string' ? hashStr(seed) : seed >>> 0;
    this.next = mulberry32(this.seed);
  }
  f() { return this.next(); }
  range(a, b) { return a + (b - a) * this.next(); }
  int(a, b) { return Math.floor(this.range(a, b + 1)); }
  sym(a) { return (this.next() * 2 - 1) * a; }
  pick(arr) { return arr[Math.floor(this.next() * arr.length)]; }
  chance(p) { return this.next() < p; }
  gauss(sd = 1) {
    let u = 0, v = 0;
    while (u === 0) u = this.next();
    v = this.next();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v) * sd;
  }
  fork(tag) { return new Rng((this.seed ^ hashStr(String(tag))) >>> 0); }
}

// Smooth 1-D value noise in [-1, 1] (cosine-free, quintic fade).
export function noise1(seed) {
  const r = mulberry32(seed >>> 0);
  const N = 256, tab = new Float32Array(N);
  for (let i = 0; i < N; i++) tab[i] = r() * 2 - 1;
  return function (x) {
    const i = Math.floor(x), f = x - i;
    const a = tab[((i % N) + N) % N], b = tab[(((i + 1) % N) + N) % N];
    const u = f * f * f * (f * (f * 6 - 15) + 10);
    return a + (b - a) * u;
  };
}

// Fractal sum of noise1, for handheld drift and paper wobble.
export function fbm1(seed, oct = 3) {
  const ns = [];
  for (let i = 0; i < oct; i++) ns.push(noise1(seed + i * 1013));
  return function (x) {
    let s = 0, a = 1, f = 1, n = 0;
    for (let i = 0; i < oct; i++) { s += ns[i](x * f) * a; n += a; a *= 0.5; f *= 2.03; }
    return s / n;
  };
}

// 2-D value noise, used for paper and washes.
export function noise2(seed) {
  const r = mulberry32(seed >>> 0);
  const N = 256, perm = new Uint16Array(N * 2), val = new Float32Array(N);
  for (let i = 0; i < N; i++) { perm[i] = i; val[i] = r(); }
  for (let i = N - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); const t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
  for (let i = 0; i < N; i++) perm[i + N] = perm[i];
  const fade = (t) => t * t * (3 - 2 * t);
  return function (x, y) {
    const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
    const X = xi & 255, Y = yi & 255;
    const v00 = val[perm[X + perm[Y]]], v10 = val[perm[X + 1 + perm[Y]]];
    const v01 = val[perm[X + perm[Y + 1]]], v11 = val[perm[X + 1 + perm[Y + 1]]];
    const u = fade(xf), v = fade(yf);
    return (v00 + (v10 - v00) * u) * (1 - v) + (v01 + (v11 - v01) * u) * v; // 0..1
  };
}
