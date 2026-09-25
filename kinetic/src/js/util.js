/* Kinetic Manifesto — shared helpers.
   Everything hangs off one namespace, K. This file must stay DOM-free at load time:
   build.mjs runs it in Node to validate content and render the page template. */
(function (root) {
  'use strict';
  const K = (root.K = root.K || {});

  K.VERSION = '2.0.0';
  K.FORMAT = 'kinetic-manifesto@1';

  /* ---------- numbers & easing ---------- */
  K.clamp = (v, lo = 0, hi = 1) => (v < lo ? lo : v > hi ? hi : v);
  K.lerp = (a, b, t) => a + (b - a) * t;
  /* position of t inside [a, b], clamped to 0..1 */
  K.span = (t, a, b) => K.clamp((t - a) / (b - a));
  K.ease = {
    linear: (t) => t,
    out3: (t) => 1 - Math.pow(1 - t, 3),
    out4: (t) => 1 - Math.pow(1 - t, 4),
    in3: (t) => t * t * t,
    inOut3: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    inOut2: (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
    /* damped spring: overshoots ~14% around t≈0.4, settles at 1 */
    spring: (t) => (t <= 0 ? 0 : t >= 1 ? 1 : 1 - Math.exp(-5 * t) * Math.cos(8 * t)),
  };

  /* ---------- seeded random ---------- */
  K.hash = function (str) {
    let h = 0x811c9dc5;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  };
  K.rng = function (seed) {
    let a = seed >>> 0;
    const next = function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    return {
      next,
      range: (lo, hi) => lo + (hi - lo) * next(),
      sign: () => (next() < 0.5 ? -1 : 1),
      shuffle(arr) {
        const a2 = arr.slice();
        for (let i = a2.length - 1; i > 0; i--) {
          const j = Math.floor(next() * (i + 1));
          [a2[i], a2[j]] = [a2[j], a2[i]];
        }
        return a2;
      },
    };
  };

  /* ---------- colour ---------- */
  K.parseHex = function (hex) {
    const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(hex || '').trim());
    if (!m) return null;
    let h = m[1];
    if (h.length === 3) h = h.replace(/./g, (c) => c + c);
    const n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  };
  K.luminance = function (hex) {
    const c = K.parseHex(hex);
    if (!c) return 0;
    const lin = c.map((v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
  };
  K.contrast = function (a, b) {
    const la = K.luminance(a), lb = K.luminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  };

  /* ---------- formatting ---------- */
  K.pad = (n, w = 2) => String(Math.max(0, Math.floor(n))).padStart(w, '0');
  K.timecode = function (seconds, fps = 24) {
    const f = Math.max(0, Math.round(seconds * fps));
    const fr = f % fps, s = Math.floor(f / fps);
    return `${K.pad(Math.floor(s / 3600))}:${K.pad(Math.floor(s / 60) % 60)}:${K.pad(s % 60)}:${K.pad(fr)}`;
  };
  K.escapeHTML = (s) =>
    String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  K.clone = (o) => JSON.parse(JSON.stringify(o));

  /* ---------- DOM (only called at runtime in a browser) ---------- */
  /* K.h('div.a.b', {attrs}, children…) */
  K.h = function (sel, attrs, ...kids) {
    const parts = sel.split('.');
    const el = document.createElement(parts[0] || 'div');
    if (parts.length > 1) el.className = parts.slice(1).join(' ');
    if (attrs) {
      for (const k in attrs) {
        const v = attrs[k];
        if (v == null || v === false) continue;
        if (k === 'text') el.textContent = v;
        else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
        else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
        else el.setAttribute(k, v === true ? '' : v);
      }
    }
    for (const kid of kids.flat()) {
      if (kid == null || kid === false) continue;
      el.appendChild(typeof kid === 'string' ? document.createTextNode(kid) : kid);
    }
    return el;
  };

  /* ---------- guarded storage ---------- */
  K.store = {
    get(key) {
      try {
        const v = root.localStorage.getItem(key);
        return v == null ? null : JSON.parse(v);
      } catch (e) {
        return null;
      }
    },
    set(key, val) {
      try {
        root.localStorage.setItem(key, JSON.stringify(val));
        return true;
      } catch (e) {
        return false;
      }
    },
    del(key) {
      try {
        root.localStorage.removeItem(key);
      } catch (e) {
        /* storage unavailable: nothing to remove */
      }
    },
  };

  K.prefersReducedMotion = function () {
    try {
      return root.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {
      return false;
    }
  };
})(typeof window !== 'undefined' ? window : globalThis);
