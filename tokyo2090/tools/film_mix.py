"""film_mix.py OUTDIR — the film's sound and the mp4s.
The Gymnopédie as the game plays it (its bar 0 on the film's first frame), the higurashi and the birds under it, up
when the shot stands on the ground and down in the air, everything fading with the picture at the end; then
  OUTDIR/tokyo2090.mp4        the master (H.264 CRF 17 + AAC, -19 LUFS)
  OUTDIR/tokyo2090_web.mp4    6 Mbps, for the site
  OUTDIR/tokyo2090_share.mp4  about 26 MB, to send"""
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
music, amb = read(os.path.join(OUT, 'music.wav')), read(os.path.join(OUT, 'amb.wav'))
n = int(round(cut['end'] * R))
out = np.zeros((n, 2), np.float32)
m0 = int(round((cut['musicOffset'] - 0.03) * R))            # a hair early: the humanised first chord may lead the beat
M = music[m0:m0 + n]; out[:len(M)] += M
# the cicadas: a gain per shot, eased across the cuts
g = np.zeros(n, np.float32)
for s in cut['shots']:
    a, b = int(s['start'] * R), min(n, int((s['start'] + s['dur']) * R))
    g[a:b] = 0.9 if s['ground'] else 0.22
k = int(0.8 * R); g = np.convolve(np.pad(g, (k, k), mode='edge'), np.ones(k) / k, mode='same')[k:-k]
A = amb[:n]; out[:len(A)] += A * g[:len(A), None] * float(os.environ.get('AMB', '1.0'))
# the end: the sound fades with the picture (the last shot's black)
f0 = int((cut['end'] - 4.2) * R); out[f0:] *= np.linspace(1, 0, n - f0)[:, None] ** 1.6
out[:int(0.05 * R)] *= np.linspace(0, 1, int(0.05 * R))[:, None]
pk = np.abs(out).max(); out *= 0.89 / max(pk, 1e-6)
print(f'mix {n / R:.2f}s, peak before {20 * np.log10(pk):.1f} dBFS')
write(os.path.join(OUT, 'mix.wav'), out)

ff = ['ffmpeg', '-hide_banner', '-y']
meas = subprocess.run(ff + ['-i', os.path.join(OUT, 'mix.wav'), '-af', 'loudnorm=I=-19:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
j = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
af = (f"loudnorm=I=-19:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
      f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
print('loudness', j['input_i'], 'LUFS ->', -19)
fps = str(cut['fps'])
src = ['-framerate', fps, '-i', os.path.join(OUT, 'frames', '%05d.jpg'), '-i', os.path.join(OUT, 'mix.wav'), '-af', af, '-ar', '48000']
master = os.path.join(OUT, 'tokyo2090.mp4')
subprocess.run(ff + src + ['-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                           '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', master], check=True, capture_output=True)
print('wrote', master, os.path.getsize(master) // 1e6, 'MB')
dur = cut['end']
for name, kbps in (('web', 6000), ('share', int(26e6 * 8 / dur / 1000) - 160)):
    o = os.path.join(OUT, f'tokyo2090_{name}.mp4'); log = os.path.join(OUT, f'x264-{name}')
    v = ['-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{kbps}k', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-passlogfile', log]
    subprocess.run(ff + ['-i', master] + v + ['-pass', '1', '-an', '-f', 'mp4', os.devnull], check=True, capture_output=True)
    subprocess.run(ff + ['-i', master] + v + ['-pass', '2', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', o], check=True, capture_output=True)
    print('wrote', o, round(os.path.getsize(o) / 1e6, 1), 'MB')
