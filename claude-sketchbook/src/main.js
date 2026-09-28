import { App } from './app.js';
import { pageTau as pageTauAt } from './timeline.js';

const params = new URLSearchParams(location.search);
const canvas = document.getElementById('c');

if (params.has('video')) {
  // Film mode: fixed square frame, driven one frame at a time from outside.
  const size = +(params.get('size') || 1080);
  document.documentElement.classList.add('video');
  canvas.style.width = size + 'px';
  canvas.style.height = size + 'px';
  const app = new App(canvas, { mode: 'video', width: size, height: size });
  const tl = app.initVideo();
  window.SKETCH = {
    app, tl,
    total: tl.total,
    frame(t) { app.videoFrame(t); return true; },
    // bring the pages' drawing up to time t without rendering (to start a chunk of the film mid-way)
    seek(t) { for (let i = 0; i < 9; i++) app.data.pages[i].advanceTo(pageTauAt(tl, i, t)); return true; },
    strokes: app.data.total,
    async renderAudio() {
      const { renderSoundtrack, wav16 } = await import('./audio/soundtrack.js');
      // the pages must be drawn from scratch for the audio's own clock: use fresh runtimes' op timings (same data)
      const res = await renderSoundtrack(tl, app.data.pages);
      const bytes = wav16(res.L, res.R);
      window.__wav = bytes;
      return { length: bytes.length, peak: res.peak };
    },
    async renderStems() {
      const { renderSoundtrack, wav16 } = await import('./audio/soundtrack.js');
      const res = await renderSoundtrack(tl, app.data.pages, null, { stems: true });
      window.__stems = { piano: wav16(res.piano[0], res.piano[1]), foley: wav16(res.foley[0], res.foley[1]) };
      return { piano: window.__stems.piano.length, foley: window.__stems.foley.length };
    },
    stemChunk(name, i, size) {
      const b = window.__stems[name].subarray(i, i + size);
      let s = '';
      for (let k = 0; k < b.length; k += 0x8000) s += String.fromCharCode.apply(null, b.subarray(k, k + 0x8000));
      return btoa(s);
    },
    wavChunk(i, size) {
      const b = window.__wav.subarray(i, i + size);
      let s = '';
      for (let k = 0; k < b.length; k += 0x8000) s += String.fromCharCode.apply(null, b.subarray(k, k + 0x8000));
      return btoa(s);
    },
  };
  window.__ready = true;
} else {
  import('./live.js').then((m) => m.startLive(canvas));
}
