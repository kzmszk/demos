// Browser shell: wires Input and a view adapter to the core (proposal §3.2 "殻（Mover）").
// update(dt): 1. apply queued Commands (whether or not enabled, so the wheel keeps working as before)
//             2. take the camera position (the camera stays the source of truth for position for now); if something
//                outside moved it, that becomes a 'place' Command so the tick log stays replayable
//             3. stop if disabled  4. frame = input.read(dt)  5. client-only mode → its update(), done
//             6. core step(); 'hold' → leave the camera alone  7. view.apply(state)
// Steps 3 and 4 are swapped against the proposal's list so turn keys are not integrated while disabled (the old
// controls returned before turning).
import { createState, toPlain } from './state.js';
import { step, command } from './step.js';
import { Input } from './input.js';

export class Mover {
  // modes: { fly: flyMode(…), … } core modes (plain cfg), or client-only modes { enter, exit, update, look?, wheel? }
  // migration: { dragSign, turnPerFrame } — temporary, keeps a city's old feel in its migration commit (§3.4)
  constructor({ view, dom, win, input = {}, modes, mode, speed, speedRange, world = {}, onUserInput, migration = null }) {
    const core = {}, client = {};
    for (const [n, m] of Object.entries(modes)) (typeof m.update === 'function' ? client : core)[n] = m;
    this.view = view; this.world = world; this.clientModes = client;
    this.cfg = { axes: view.axes, modes: core, speedRange };
    this.enabled = true; this.queue = []; this.recording = null;
    const r = view.read();
    this.state = createState({ mode, speed, pos: r.pos, yaw: r.yaw, pitch: r.pitch });
    this.input = new Input({ win, dom, options: input, migration, hooks: {
      enabled: () => this.enabled,
      mode: () => this.state.mode,
      speed: () => this.speed,
      setSpeed: (value) => this.queue.push({ type: 'setSpeed', value }),
      look: (dx, dy, e) => { const m = this.clientModes[this.state.mode]; if (!m || !m.look) return false; m.look(dx, dy, e); return true; },
      wheel: (e) => { const m = this.clientModes[this.state.mode]; if (!m || !m.wheel) return false; m.wheel(e); return true; },
      userInput: onUserInput,
    } });
    this.input.yaw = r.yaw; this.input.pitch = r.pitch;
  }

  apply(cmd) {
    if (cmd.type === 'setMode') {
      const prev = this.state.mode, a = this.clientModes[prev], b = this.clientModes[cmd.name];
      if (a && a.exit) a.exit(this);
      command(this.state, cmd, this.world, this.cfg);
      if (b && b.enter) b.enter(this, prev);
    } else command(this.state, cmd, this.world, this.cfg);
  }

  update(dt) {
    const s = this.state, cmds = this.queue;
    this.queue = [];
    for (const c of cmds) this.apply(c);
    const p = this.view.readPos();
    if (p.x !== s.pos.x || p.y !== s.pos.y || p.z !== s.pos.z) { const c = { type: 'place', pos: p }; cmds.push(c); this.apply(c); }
    let frame = null;
    const client = this.clientModes[s.mode];
    if (this.enabled) frame = this.input.read(dt);
    if (this.recording) this.recording.ticks.push({ dt, cmds, frame: client ? null : frame });
    if (!frame) return;
    if (client) { client.update(this, frame, dt); return; }
    step(s, frame, dt, this.world, this.cfg);
    if (s.status === 'hold') return;
    this.view.apply(s);
  }

  // { initial: plain state, ticks: [{ dt, cmds, frame }] } — replay with fromPlain(initial), then per tick
  // command() each cmd and step() when frame is not null
  startRecording() { this.recording = { initial: toPlain(this.state), ticks: [] }; return this.recording; }

  setMode(name) { this.queue.push({ type: 'setMode', name }); }
  syncFromCamera() {
    const r = this.view.read();
    this.input.yaw = r.yaw; this.input.pitch = r.pitch;
    this.queue.push({ type: 'place', pos: r.pos, yaw: r.yaw, pitch: r.pitch });
  }
  resetInput() { this.input.reset(); }
  dispose() { this.input.dispose(); }

  // compatibility properties for the cities' existing callers
  get yaw() { return this.input.yaw; } set yaw(v) { this.input.yaw = v; }
  get pitch() { return this.input.pitch; } set pitch(v) { this.input.pitch = v; }
  get vel() { return this.state.vel; }
  get keys() { return this.input.keys; }
  get mode() { return this.state.mode; } set mode(name) { this.setMode(name); }
  // the speed asked for: a wheel turn reads (and shows) the value it queued, before the next update applies it
  get speed() {
    for (let i = this.queue.length - 1; i >= 0; i--) if (this.queue[i].type === 'setSpeed') return this.queue[i].value;
    return this.state.speed;
  }
  set speed(value) { this.queue.push({ type: 'setSpeed', value }); }
}
