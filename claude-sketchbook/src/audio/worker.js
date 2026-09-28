// Background renderer for the piano (live mode): sections of the score → dry stereo buffers.
import { buildScore, perform } from './score.js';
import { SR } from './piano.js';
import { mixSection, balance } from './soundtrack.js';

const score = buildScore();
const KEYS = ['intro', 'p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09', 'end'];
self.onmessage = (e) => {
  const { key } = e.data;
  const k = KEYS.indexOf(key);
  const perf = perform(score[key], 1000 + k);
  const n = Math.ceil((perf.dur + 6) * SR);
  const buf = [new Float32Array(n), new Float32Array(n)];
  mixSection(buf, perf, 0, 50 + k);
  balance(buf);
  self.postMessage({ key, L: buf[0], R: buf[1], dur: perf.dur }, [buf[0].buffer, buf[1].buffer]);
};
