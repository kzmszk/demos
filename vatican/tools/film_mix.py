"""film_mix.py OUTDIR — the film's sound: the score cut (the approach, bars 0-8, then the square from its bar 4; the first part's last chord left
to ring under the cut), the natural sounds the frames heard on top, a fade at the end; then the frames and the sound
into OUTDIR/vaticano.mp4 (H.264 + AAC, loudness -16 LUFS)."""
import json, os, subprocess, sys, wave
import numpy as np

OUT = sys.argv[1]
R = 48000

def read(p):
    with wave.open(p) as w:
        assert w.getframerate() == R and w.getnchannels() == 2
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768

def write(p, x):
    with wave.open(p, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(R)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

cut = json.load(open(os.path.join(OUT, 'cut.json')))
music, amb = read(os.path.join(OUT, 'music_full.wav')), read(os.path.join(OUT, 'amb.wav'))
a, b, end = (int(round(cut[k] * R)) for k in ('a', 'b', 'end'))
n = end
out = np.zeros((n, 2), np.float32)
out[:a] = music[:a]
# the second part from bar 32 on, hard on the downbeat (20 ms in, no click), and the first part's tail fading under it
B = music[b:b + (n - a)]
ramp = np.minimum(1.0, np.arange(len(B)) / (0.02 * R))[:, None]
out[a:a + len(B)] += B * ramp
tl = int(1.6 * R); T = music[a:a + tl]
out[a:a + len(T)] += T * (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, len(T))))[:, None]
# the natural sounds, as rendered against the frames
m = min(n, len(amb)); out[:m] += amb[:m] * float(os.environ.get('AMB', '1.0'))
# the end: everything fades with the picture
f0 = int((cut['end'] - 2.6) * R); out[f0:] *= np.linspace(1, 0, n - f0)[:, None] ** 1.5
pk = np.abs(out).max(); out *= 0.89 / max(pk, 1e-6)
print(f'mix {n / R:.2f}s, music cut at {cut["a"]:.3f}s -> {cut["b"]:.3f}s, peak before {20 * np.log10(pk):.1f} dBFS')
write(os.path.join(OUT, 'mix.wav'), out)

# loudness: measure, then one linear gain to -16 LUFS (true peak under -1.5 dB)
ff = ['ffmpeg', '-hide_banner', '-y']
meas = subprocess.run(ff + ['-i', os.path.join(OUT, 'mix.wav'), '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
j = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
af = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
      f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
print('loudness', j['input_i'], 'LUFS ->', -16)
subprocess.run(ff + ['-framerate', '30', '-i', os.path.join(OUT, 'frames', '%05d.jpg'), '-i', os.path.join(OUT, 'mix.wav'),
                     '-af', af, '-ar', '48000', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                     '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', os.path.join(OUT, 'vaticano.mp4')], check=True,
               capture_output=True)
print('wrote', os.path.join(OUT, 'vaticano.mp4'))
