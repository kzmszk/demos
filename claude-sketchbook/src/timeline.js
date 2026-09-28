// The film: when everything happens, as pure functions of time t (seconds). The score is written to it.
export const BPM = 76;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 3; // 3/4
export const INTRO_BARS = 4, PAGE_BARS = 8, END_BARS = 4;
export const TAIL = 5.5;

const smooth = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));
const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);

// A speed profile for time-lapse drawing: starts near real time, runs fast, eases out.
export function makeWarp(T, D, s0 = 2.2, s1 = 4, a = 2.6, b = 1.6) {
  const vm = Math.max(s0, (T - (s0 * a) / 2 - (s1 * b) / 2) / (D - a / 2 - b / 2));
  const N = 400, tab = new Float64Array(N + 1);
  let acc = 0;
  const v = (t) => s0 + (vm - s0) * smooth(t / a) - (vm - s1) * smooth((t - (D - b)) / b);
  for (let i = 1; i <= N; i++) {
    const t0 = ((i - 1) / N) * D, t1 = (i / N) * D;
    acc += ((v(t0) + v(t1)) / 2) * (t1 - t0);
    tab[i] = acc;
  }
  const k = T / acc; // normalise so the page finishes exactly on time
  for (let i = 0; i <= N; i++) tab[i] *= k;
  return {
    tau(t) { const x = clamp01(t / D) * N; const i = Math.min(N - 1, Math.floor(x)); return tab[i] + (tab[i + 1] - tab[i]) * (x - i); },
    inv(tau) {
      if (tau <= 0) return 0;
      if (tau >= T) return D;
      let lo = 0, hi = N;
      while (hi - lo > 1) { const m = (lo + hi) >> 1; if (tab[m] < tau) lo = m; else hi = m; }
      return ((lo + (tau - tab[lo]) / (tab[hi] - tab[lo])) / N) * D;
    },
    vmax: vm * k,
  };
}

// pages: [{T}] natural durations for p01..p09 (p10 is blank)
export function buildTimeline(pages) {
  const ev = {};
  const intro = INTRO_BARS * BAR;
  ev.pencilOut = [3.5, 4.9];
  ev.band = [4.95, 5.65];
  ev.cover = [5.85, 8.35];
  ev.intro = intro;
  const sec = [];
  for (let i = 0; i < 9; i++) {
    const s0 = intro + i * PAGE_BARS * BAR, s1 = s0 + PAGE_BARS * BAR;
    const left = i % 2 === 1; // p2, p4 … sit on the left
    const turn = left ? [s0 + 0.05, s0 + 1.75] : null; // the leaf goes over at the top of the section
    const d0 = (turn ? turn[1] + 0.35 : s0 + (i === 0 ? 0.55 : 0.75));
    const d1 = s1 - 0.55;
    const warp = makeWarp(pages[i].T, d1 - d0);
    sec.push({ i, s0, s1, turn, d0, d1, warp, side: left ? 'L' : 'R' });
  }
  const e0 = intro + 9 * PAGE_BARS * BAR;
  const end = { s0: e0, s1: e0 + END_BARS * BAR, turn: [e0 + 0.05, e0 + 1.75] };
  const total = end.s1 + TAIL;
  return { ev, sec, end, total, intro };
}

// page natural time at global t (null if not yet started)
export function pageTau(tl, i, t) {
  const s = tl.sec[i];
  if (t < s.d0) return 0;
  return s.warp.tau(t - s.d0);
}

// the global time at which page i reaches natural time tau
export function globalAt(tl, i, tau) {
  const s = tl.sec[i];
  return s.d0 + s.warp.inv(tau);
}

export function leafTurn(tl, leaf, t) {
  // leaf k is turned at the start of section 2k+1 (p2, p4 …); leaf 4 at the end section
  const turn = leaf < 4 ? tl.sec[leaf * 2 + 1].turn : tl.end.turn;
  return clamp01((t - turn[0]) / (turn[1] - turn[0]));
}

export { smooth, clamp01 };
