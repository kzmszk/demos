// Sound for a person turning pages: the score follows the page you are on, bar by bar; the foley follows the pencil.
import { SR } from './piano.js';
import { makeIR } from './reverb.js';
import { buildScore, perform } from './score.js';
import { mixSection, balance, roomTone, MIX_GAIN } from './soundtrack.js';
import { BAR } from '../timeline.js';
import * as FX from './sfx.js';
import { Rng } from '../rng.js';

/* global __WORKER__ */
export class LiveAudio {
  constructor() {
    const AC = window.AudioContext || window.webkitAudioContext;
    this.ctx = new AC({ sampleRate: SR, latencyHint: 'playback' });
    const c = this.ctx;
    this.master = c.createGain();
    this.master.gain.value = 0.9;
    const comp = c.createDynamicsCompressor();
    comp.threshold.value = -12; comp.knee.value = 10; comp.ratio.value = 1.7; comp.attack.value = 0.025; comp.release.value = 0.4;
    this.master.connect(comp); comp.connect(c.destination);
    const ir = makeIR(SR);
    const irb = c.createBuffer(2, ir[0].length, SR); irb.copyToChannel(ir[0], 0); irb.copyToChannel(ir[1], 1);
    this.conv = c.createConvolver(); this.conv.normalize = false; this.conv.buffer = irb;
    this.conv.connect(this.master);
    this.pianoBus = c.createGain(); this.pianoBus.gain.value = MIX_GAIN; // the film is peak-normalised to about this
    const pw = c.createGain(); pw.gain.value = 0.42;
    this.pianoBus.connect(this.master); this.pianoBus.connect(pw); pw.connect(this.conv);
    this.foleyBus = c.createGain(); this.foleyBus.gain.value = 1.8 * MIX_GAIN;
    const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 8500; lp.Q.value = 0.6;
    const fw = c.createGain(); fw.gain.value = 0.12;
    this.foleyBus.connect(lp); lp.connect(this.master); lp.connect(fw); fw.connect(this.conv);
    // a quiet room
    const rt = [new Float32Array(SR * 4), new Float32Array(SR * 4)];
    roomTone(rt, 77);
    const rb = c.createBuffer(2, rt[0].length, SR); rb.copyToChannel(rt[0], 0); rb.copyToChannel(rt[1], 1);
    const rs = c.createBufferSource(); rs.buffer = rb; rs.loop = true;
    const rg = c.createGain(); rg.gain.value = MIX_GAIN * 1.8; rs.connect(rg); rg.connect(this.master); rs.start();
    this.sections = new Map();
    this.pending = new Map();
    this.cur = null;
    this.startWorker();
    this.muted = false;
    this.scratch = null;
  }
  startWorker() {
    try {
      const src = typeof __WORKER__ !== 'undefined' ? __WORKER__ : null;
      if (!src) throw new Error('no worker source');
      this.worker = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
      this.worker.onmessage = (e) => this.onSection(e.data);
      this.worker.onerror = () => { this.worker = null; };
    } catch (e) { this.worker = null; }
  }
  onSection({ key, L, R, dur }) {
    const b = this.ctx.createBuffer(2, L.length, SR);
    b.copyToChannel(L, 0); b.copyToChannel(R, 1);
    this.sections.set(key, { buf: b, dur });
    const p = this.pending.get(key);
    if (p) { this.pending.delete(key); p.forEach((f) => f()); }
  }
  // make sure a section is (being) rendered
  prepare(key) {
    if (this.sections.has(key) || this.pending.has(key)) return;
    this.pending.set(key, []);
    if (this.worker) this.worker.postMessage({ key });
    else setTimeout(() => {
      // no worker: render here (a short stall, once per section)
      const KEYS = ['intro', 'p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09', 'end'];
      const k = KEYS.indexOf(key);
      const perf = perform(buildScore()[key], 1000 + k);
      const n = Math.ceil((perf.dur + 6) * SR);
      const buf = [new Float32Array(n), new Float32Array(n)];
      mixSection(buf, perf, 0, 50 + k);
      balance(buf);
      this.onSection({ key, L: buf[0], R: buf[1], dur: perf.dur });
    }, 30);
  }
  resume() { if (this.ctx.state !== 'running') this.ctx.resume(); }
  get now() { return this.ctx.currentTime; }
  // the next bar line of whatever is playing (or now)
  nextBar(lead = 0.08) {
    const t = this.now + lead;
    if (!this.cur) return t;
    const k = Math.ceil((t - this.cur.start) / BAR - 1e-6);
    return this.cur.start + Math.max(0, k) * BAR;
  }
  // play a section at the next bar line; the previous one lets go like a lifted pedal
  play(key, opts = {}) {
    this.prepare(key);
    const go = () => {
      const s = this.sections.get(key);
      const at = opts.now ? this.now + 0.05 : this.nextBar();
      if (this.cur) {
        const g = this.cur.gain.gain;
        g.cancelScheduledValues(at);
        g.setValueAtTime(g.value, at);
        g.setTargetAtTime(0, at + 0.02, 0.35);
        this.cur.src.stop(at + 3);
      }
      const src = this.ctx.createBufferSource();
      src.buffer = s.buf;
      const gain = this.ctx.createGain();
      gain.gain.value = opts.gain ?? 1;
      src.connect(gain); gain.connect(this.pianoBus);
      src.start(at);
      this.cur = { key, src, gain, start: at, end: at + s.dur, loop: opts.loop ?? true };
    };
    if (this.sections.has(key)) go();
    else this.pending.get(key).push(go);
  }
  // called every frame: keep the music going (loop the current section, gently)
  tick() {
    if (!this.cur || !this.cur.loop) return;
    if (this.now > this.cur.end - 0.25 && !this.cur.looping) {
      this.cur.looping = true;
      const key = this.cur.key, at = this.cur.end;
      const s = this.sections.get(key);
      const src = this.ctx.createBufferSource(); src.buffer = s.buf;
      const gain = this.ctx.createGain(); gain.gain.value = 0.85;
      src.connect(gain); gain.connect(this.pianoBus);
      src.start(at);
      this.cur = { key, src, gain, start: at, end: at + s.dur, loop: true };
    }
  }
  // a one-shot foley buffer built by fn(buf) (stereo Float32 pair), played at ctx time `at`
  foley(seconds, fn, at, gain = 1) {
    const n = Math.ceil(seconds * SR);
    const buf = [new Float32Array(n), new Float32Array(n)];
    fn(buf);
    const b = this.ctx.createBuffer(2, n, SR);
    b.copyToChannel(buf[0], 0); b.copyToChannel(buf[1], 1);
    const s = this.ctx.createBufferSource(); s.buffer = b;
    const g = this.ctx.createGain(); g.gain.value = gain;
    s.connect(g); g.connect(this.foleyBus);
    s.start(Math.max(this.now, at ?? this.now));
    return { src: s, gain: g };
  }
  stopFoley(h) {
    if (!h) return;
    const t = this.now;
    h.gain.gain.cancelScheduledValues(t);
    h.gain.gain.setTargetAtTime(0, t, 0.05);
    h.src.stop(t + 0.4);
  }
  // the reader's own pencil: a looped scratch whose level follows the pointer
  scratchStart() {
    if (this.scratch) return;
    const n = SR * 2;
    const buf = [new Float32Array(n), new Float32Array(n)];
    FX.scribble(buf, 0, 1.98, { medium: 'pencil', speed: 1, gain: 1, pan: -0.25 }, 99);
    const b = this.ctx.createBuffer(2, n, SR); b.copyToChannel(buf[0], 0); b.copyToChannel(buf[1], 1);
    const s = this.ctx.createBufferSource(); s.buffer = b; s.loop = true; s.loopStart = 0.02; s.loopEnd = 1.95;
    const g = this.ctx.createGain(); g.gain.value = 0;
    s.connect(g); g.connect(this.foleyBus); s.start();
    this.scratch = { s, g };
  }
  scratchLevel(v) { if (this.scratch) this.scratch.g.gain.setTargetAtTime(Math.min(0.03, v * 0.012), this.now, 0.02); }
  setMuted(m) {
    this.muted = m;
    this.master.gain.setTargetAtTime(m ? 0 : 0.9, this.now, 0.08);
  }
}
