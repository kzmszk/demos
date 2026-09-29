// ffmpeg / ffprobe helpers shared by the publisher and the on-request job.
import { run, round } from './util.mjs';

export const ffmpeg = (args) => run('ffmpeg', ['-y', '-loglevel', 'error', ...args], { check: true });

/** The light copy is the deliverable: 1080p H.264 + AAC, about a quarter of the size of the render, playable while it downloads (+faststart). */
export const makeLightCopy = (src, dst) => ffmpeg(['-i', src, '-c:v', 'libx264', '-preset', 'slow', '-crf', '22', '-tune', 'animation', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '160k', dst]);

export const posterFrame = (video, t, out) => ffmpeg(['-ss', String(t), '-i', video, '-frames:v', '1', '-vf', 'scale=1280:720:flags=lanczos', '-c:v', 'libwebp', '-quality', '86', out]);

export async function probe(file) {
  const j = JSON.parse((await run('ffprobe', ['-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', file], { check: true })).stdout);
  const v = j.streams.find((s) => s.codec_type === 'video');
  const [n, d] = v.r_frame_rate.split('/').map(Number);
  return { seconds: round(+j.format.duration, 3), width: v.width, height: v.height, fps: round(n / (d || 1), 2) };
}
