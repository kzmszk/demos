// build_goldberg_web.mjs — a compact copy of the Goldberg score for the browser.
//   node build_goldberg_web.mjs      reads  kyoto-assets/score/goldberg.json  (CC BY-SA 4.0, see CREDITS.txt there)
//                                    writes public/data/goldberg.json
// The source file already holds the slow playback tempo of each movement in `bpm_original` (quarter notes per minute;
// the Aria 40, Var. 25 24 ...). The browser tempo is that, except for the quick movements (>= 100) which are taken down
// a tenth again, so that their sixteenths stay clear in a warm room.
// Per movement: id, title, title_ja, meter, bpm (play tempo), tempo_map ([[beat, bpm], ...] only where it changes: Var. 16),
// total_beats, bar_beats (start of each bar, in beats), notes [[t, dur, midi, vel], ...] (beats, rounded to 1/960).
import fs from 'node:fs'; import path from 'node:path';
const HERE = path.dirname(new URL(import.meta.url).pathname);
const SRC = '/home/kazu/work/kyoto-assets/score/goldberg.json', OUT = path.resolve(HERE, '../public/data/goldberg.json');
const d = JSON.parse(fs.readFileSync(SRC, 'utf8'));
const q = (x) => +(Math.round(x * 960) / 960).toFixed(4);
const tempo = (b) => (b >= 100 ? b * 0.9 : b);
const r1 = (x) => +x.toFixed(2);
const out = {
  source: 'J. S. Bach, Goldberg Variations BWV 988 — Open Goldberg Variations (Kimiko Ishizaka, CC0) as engraved in LilyPond by Knute Snortum (CC BY-SA 4.0); see CREDITS.txt',
  licence: 'CC BY-SA 4.0 — Knute Snortum / Open Goldberg Variations; Bach: public domain',
  note_format: '[t_beats, dur_beats, midi, vel]  beats are quarter notes from the start of the movement; seconds = beats * 60 / bpm; repeats expanded',
  movements: d.movements.map((m) => {
    const scale = tempo(m.bpm_original) / m.bpm_original;
    const map = m.tempo_map.length > 1 ? m.tempo_map.map(([b, t]) => [b, r1(t * scale)]) : null;
    const o = { id: m.id, title: m.title, title_ja: m.title_ja, meter: m.meter, bpm: r1(map ? map[0][1] : tempo(m.bpm_original)) };
    if (map) o.tempo_map = map;
    o.total_beats = m.total_beats;
    o.bar_beats = m.bar_beats.map(q);
    o.notes = m.notes.map(([t, dur, midi, vel]) => [q(t), q(dur), midi, vel]);
    return o;
  }),
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out));
let secs = 0;
for (const m of out.movements) {
  const tm = m.tempo_map || [[0, m.bpm]];
  let s = 0; for (let i = 0; i < tm.length; i++) { const b0 = tm[i][0], b1 = i + 1 < tm.length ? tm[i + 1][0] : m.total_beats; s += ((b1 - b0) * 60) / tm[i][1]; }
  secs += s; console.log(m.id.padEnd(13), String(m.bpm).padStart(6), (s / 60).toFixed(2) + ' min', m.notes.length + ' notes');
}
console.log('total', (secs / 60).toFixed(1), 'min;', (fs.statSync(OUT).size / 1024).toFixed(0), 'KiB ->', OUT);
