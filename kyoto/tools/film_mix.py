"""film_mix.py OUTDIR — the film's sound (after venice/tools/film_mix.py): the Aria's opening bars (music_a.wav), then its
close from bar 60 (music_b.wav) hard on the downbeat with the first part's last notes left to ring under the cut, the
natural sounds the frames heard on top (amb.wav), a fade at the end; then frames + sound into OUTDIR/kyoto.mp4 (H.264 + AAC,
-16 LUFS) and a smaller OUTDIR/kyoto_share.mp4 for phones (about 26 MB)."""
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

def onset(x):
    """the first note: the first sample over 3 % of the render's peak (a few ms before it, for the attack)"""
    e = np.abs(x).max(1); i = int(np.argmax(e > 0.03 * e.max()))
    return max(0, i - int(0.004 * R))

cut = json.load(open(os.path.join(OUT, 'cut.json')))
A, B, amb = read(os.path.join(OUT, 'music_a.wav')), read(os.path.join(OUT, 'music_b.wav')), read(os.path.join(OUT, 'amb.wav'))
oA, oB = onset(A), onset(B)
t0, c, end = (int(round(cut[k] * R)) for k in ('t0', 'cut', 'end'))
n = end
out = np.zeros((n, 2), np.float32)
# the opening: bar 0 at film time t0
la = c - t0; out[t0:c] = A[oA:oA + la]
# the close: bar 60 on the cut's downbeat (20 ms in: no click)
Bp = B[oB:oB + (n - c)]
out[c:c + len(Bp)] += Bp * np.minimum(1.0, np.arange(len(Bp)) / (0.02 * R))[:, None]
# the first part's last notes ring on under it
tl = int(1.8 * R); T = A[oA + la:oA + la + tl]
out[c:c + len(T)] += T * (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, len(T))))[:, None]
# the natural sounds (water, weirs, footsteps, bells), as rendered against the frames
m = min(n, len(amb)); out[:m] += amb[:m] * float(os.environ.get('AMB', '1.0'))
# the end: everything fades with the picture
f0 = int((cut['end'] - 3.0) * R); out[f0:] *= np.linspace(1, 0, n - f0)[:, None] ** 1.5
pk = np.abs(out).max(); out *= 0.89 / max(pk, 1e-6)
print(f'mix {n / R:.2f}s, onsets {oA / R:.3f}s / {oB / R:.3f}s, cut at {c / R:.3f}s, peak before {20 * np.log10(pk):.1f} dBFS')
write(os.path.join(OUT, 'mix.wav'), out)

# the picture starts with the music (frame t0 * fps): the lead-in holds the first frame
FR = os.path.join(OUT, 'frames'); first = min(int(f[:5]) for f in os.listdir(FR) if f.endswith('.jpg'))
for k in range(first):
    p_ = os.path.join(FR, f'{k:05d}.jpg')
    if not os.path.exists(p_): import shutil; shutil.copy(os.path.join(FR, f'{first:05d}.jpg'), p_)
ff = ['ffmpeg', '-hide_banner', '-y']
meas = subprocess.run(ff + ['-i', os.path.join(OUT, 'mix.wav'), '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
j = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
af = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
      f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
print('loudness', j['input_i'], 'LUFS ->', -16)
master = os.path.join(OUT, 'kyoto.mp4')
subprocess.run(ff + ['-framerate', '30', '-i', os.path.join(OUT, 'frames', '%05d.jpg'), '-i', os.path.join(OUT, 'mix.wav'),
                     '-af', af, '-ar', '48000', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                     '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', master], check=True, capture_output=True)
print('wrote', master, os.path.getsize(master) // 2 ** 20, 'MB')
# for phones (the app's file sending stops at 30 MiB): two-pass at a bitrate for about 26 MB
dur = n / R; vb = int((26 * 8 * 2 ** 20 / dur - 160e3) / 1e3)
share = os.path.join(OUT, 'kyoto_share.mp4'); pl = os.path.join(OUT, 'x264pass')
for ps in (1, 2):
    subprocess.run(ff + ['-i', master, '-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{vb}k', '-pass', str(ps), '-passlogfile', pl, '-pix_fmt', 'yuv420p']
                   + (['-an', '-f', 'mp4', os.devnull] if ps == 1 else ['-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', share]), check=True, capture_output=True)
print('wrote', share, os.path.getsize(share) // 2 ** 20, 'MB', f'({vb} kbit/s video)')
