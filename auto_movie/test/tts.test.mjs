// Gemini TTS: request shape and response decoding, with fetch stubbed (no key, no network).
import test from 'node:test';
import assert from 'node:assert/strict';
import { encodeWav } from '../lib/audio/wav.mjs';
import * as gemini from '../lib/tts/gemini.mjs';

const wav24k = () => encodeWav({ rate: 24000, channels: [Float32Array.from({ length: 24000 }, (_, i) => 0.3 * Math.sin(i / 20))] });

test('Gemini interactions API: request and audio decoding', async () => {
  process.env.GEMINI_API_KEY = 'test-key';
  const calls = [];
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), body: JSON.parse(init.body), headers: init.headers });
    return new Response(JSON.stringify({ steps: [{ type: 'model_output', content: [{ type: 'audio', data: wav24k().toString('base64') }] }] }), { status: 200 });
  };
  try {
    const r = await gemini.synth({ text: 'こんにちは。', voice: 'Kore', style: 'やさしく' });
    assert.equal(calls.length, 1);
    assert.match(calls[0].url, /v1beta\/interactions$/);
    assert.equal(calls[0].headers['x-goog-api-key'], 'test-key');
    assert.equal(calls[0].body.generation_config.speech_config[0].voice, 'Kore');
    assert.equal(calls[0].body.input[0].content[0].annotations[0].style, 'やさしく');
    assert.equal(r.rate, 24000);
    assert.ok(Math.abs(r.duration - 1) < 0.01);
  } finally { globalThis.fetch = realFetch; }
});

test('Gemini falls back to generateContent (raw L16 PCM) when the interactions API is rejected', async () => {
  process.env.GEMINI_API_KEY = 'test-key';
  const realFetch = globalThis.fetch;
  const pcm = Buffer.alloc(48000); for (let i = 0; i < 24000; i++) pcm.writeInt16LE(Math.round(8000 * Math.sin(i / 15)), i * 2);
  let n = 0;
  globalThis.fetch = async (url) => {
    n++;
    if (String(url).endsWith('/interactions')) return new Response('not found', { status: 404 });
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ inlineData: { mimeType: 'audio/L16;codec=pcm;rate=24000', data: pcm.toString('base64') } }] } }] }), { status: 200 });
  };
  try {
    const r = await gemini.synth({ text: 'テスト。', voice: 'Puck' });
    assert.equal(n, 2);
    assert.equal(r.rate, 24000);
    assert.ok(Math.abs(r.duration - 1) < 0.01);
  } finally { globalThis.fetch = realFetch; }
});
