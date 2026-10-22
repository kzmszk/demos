# Asturias: nylon-guitar opening study

This is a sequenced, sampled-guitar prototype, not a recording of a guitarist
and not a generative-model performance. It is not the complete work.

## Musical source

Isaac Albéniz (1860–1909), *Chants d'Espagne*, Op.232 No.1, Prélude
(later known as Asturias / Leyenda). The first 24 measures were entered by hand
from printed page 2 of the early piano edition/reprint, plate 22, Casa Dotesio,
held by the Sibley Music Library / University of Rochester:

- Catalogue: https://hdl.handle.net/1802/13306
- Scan: https://urresearch.rochester.edu/fileDownloadForInstitutionalItem.action?itemId=13007&itemFileId=30118
- PDF SHA256: `a6b7ae0b735c8d36a6ffa43b02eb0cc3ae01a9316e150b257adea2d4a1ed7480`
- Edition metadata: https://imslp.org/wiki/Chants_d%27Espagne,_Op.232_(Alb%C3%A9niz,_Isaac)

The original work and this early edition are public domain. No modern guitar
edition or existing performance MIDI was copied. This study transposes G minor
to E minor, reduces piano doubling, adjusts articulation and dynamics, and adds
a short B7–E-minor cadence after measure 24 to finish the excerpt. This ending
is our addition, not Albéniz's original ending. The pitches in `bars` remain in
the original key to make comparison with the source easier.

## Instrument attribution

Nylon guitar samples: **FluidR3**, Frank Wen and contributors, pre-rendered by
**Benjamin Gleitzman / midi-js-soundfonts**.

- Project: https://github.com/gleitz/midi-js-soundfonts
- Sample bank: https://gleitz.github.io/midi-js-soundfonts/FluidR3_GM/acoustic_guitar_nylon-mp3.js
- That distribution labels its Fluid samples **CC BY 3.0**:
  https://creativecommons.org/licenses/by/3.0/
- Source SHA256: `5375fa9e0408d960e12b6e4ec120c42bce824d80b18e982b27ddaece146a4f64`

Changes: extracted individual notes, mono decoding, note timing, damping,
velocity and tone adjustment, short stereo reflections, normalization and MP3
encoding. Credit these sources when publishing the audio. The generated studies
are made available under CC BY 3.0 with the above attribution.

## Reproduce

Requires Node.js and ffmpeg (already present when generated). No API key, Python
package, system installation, or hosted synthesis service is needed.

```sh
mkdir -p alhambra/tools/music/.cache
curl --fail --location \
  https://gleitz.github.io/midi-js-soundfonts/FluidR3_GM/acoustic_guitar_nylon-mp3.js \
  --output alhambra/tools/music/.cache/nylon.js
node alhambra/tools/music/render-asturias.mjs
```

The renderer verifies the bank checksum and parses its data without executing
downloaded JavaScript. Output:

- `alhambra/public/audio/asturias-study.mp3`: 132 quarter notes/minute.
- `alhambra/public/audio/asturias-brisk.mp3`: 152 quarter notes/minute.
- `.cache/asturias-*.wav`: uncompressed local masters.
- `asturias-*-events.json`: reproducible event timing and dynamics.
- `asturias-render.json`: duration, peak, RMS and note counts.

## App arrangement

`node alhambra/tools/music/render-asturias.mjs --full` creates
`alhambra/public/audio/asturias-full.mp3` (about 5:37, 192 kbps stereo).
`asturias-score.mjs` independently reduces the early piano score on printed
pages 2–7 into a sampled-guitar arrangement, including the fast main section,
cantando middle section, reprise and coda. It simplifies octave doubling,
ornaments, accompaniment and voicing; it is not an urtext note-for-note edition.
The opening excerpt's added cadence is not used in this longer version.

The fast sections use 152 BPM; the lyrical section and coda vary in tempo.
`asturias-sections.json` records section boundaries for QA. The app streams
this MP3 only after Play, repeats after the final decay, remembers volume,
and keeps music independent of water ambience. Public attribution appears
at `credits.html#music`.

A CC BY MIDI source was investigated but could not be downloaded; no MIDI or
arrangement from that source is incorporated. The longer version was entered
from the public-domain scan instead. No new library installation is required.
